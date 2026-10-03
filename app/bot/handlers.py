"""Telegram message and callback handlers for ChronoDump."""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    get_clarification_keyboard,
    get_degraded_arm_keyboard,
    get_reminder_action_keyboard,
    get_reminder_confirm_done_keyboard,
    get_reminder_undo_keyboard,
    get_timezone_keyboard,
)
from app.bot.messages import (
    format_confirm_completion,
    format_response_card,
    format_start_welcome,
    format_task_completed,
    format_task_restored,
    format_task_snoozed,
    format_timezone_prompt,
    format_timezone_updated,
)
from app.config import settings
from app.ingestion.audio import AudioIngestion
from app.ingestion.text import TextIngestion
from app.intelligence.llm import LLMClient
from app.intelligence.temporal import TemporalEngine
from app.scheduler.jobs import scheduler_service
from app.storage.database import (
    complete_reminder,
    create_dump,
    create_reminder,
    create_vague_clarification,
    get_or_create_user,
    get_reminder,
    get_user_timezone,
    get_vague_clarification,
    resolve_vague_clarification,
    snooze_reminder,
    undo_complete_reminder,
    update_user_timezone,
)

logger = logging.getLogger(__name__)

router = Router(name="main_router")
audio_ingestion = AudioIngestion()
text_ingestion = TextIngestion()
llm_client = LLMClient()


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start command — welcome user and prompt for timezone setup."""
    if not message.from_user:
        return
    user = get_or_create_user(message.from_user.id)
    await message.answer(
        format_start_welcome(user.telegram_id),
        reply_markup=get_timezone_keyboard(),
        parse_mode="Markdown",
    )


@router.message(Command("timezone"))
async def handle_timezone_command(message: Message) -> None:
    """Handle /timezone command — show and allow changing timezone."""
    if not message.from_user:
        return
    user_tz = get_user_timezone(message.from_user.id)
    await message.answer(
        format_timezone_prompt(str(user_tz)),
        reply_markup=get_timezone_keyboard(),
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command with usage overview."""
    text = (
        "🤖 **ChronoDump Help**\n\n"
        "• Send or forward a **voice note** or **text message** containing your thoughts, tasks, and deadlines.\n"
        "• ChronoDump cleans up the notes, extracts tasks, and automatically arms reminders.\n"
        "• If deadlines are vague (e.g. _this weekend_), ChronoDump will ask for clarification at the right moment.\n\n"
        "**Commands:**\n"
        "/start — Welcome & setup\n"
        "/timezone — Change timezone\n"
        "/help — Show this guide"
    )
    await message.answer(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Timezone Callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("tz:"))
async def handle_timezone_callback(callback: CallbackQuery) -> None:
    """Handle timezone selection button clicks."""
    if not callback.data or not callback.from_user:
        return
    selected_tz = callback.data.split(":", 1)[1]

    if selected_tz == "custom":
        await callback.message.edit_text(
            "Please reply with your standard IANA timezone (e.g. `America/Chicago`, `Europe/London`, `Asia/Tokyo`) or UTC offset (e.g. `+05:30`, `-04:00`):",
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    success = update_user_timezone(callback.from_user.id, selected_tz)
    if success:
        await callback.message.edit_text(
            format_timezone_updated(selected_tz),
            parse_mode="Markdown",
        )
        await callback.answer(f"Timezone set to {selected_tz}")
    else:
        await callback.answer("Invalid timezone. Please try another.", show_alert=True)


# ---------------------------------------------------------------------------
# Reminder Action Callbacks (Done, Confirm, Cancel, Undo, Snooze)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("rem:done:"))
async def handle_reminder_done_click(callback: CallbackQuery) -> None:
    """Step 1 of completion: prompt for confirmation (PRD Section 18)."""
    reminder_id = int(callback.data.split(":")[2])
    reminder = get_reminder(reminder_id)
    if not reminder:
        await callback.answer("Reminder not found.", show_alert=True)
        return

    await callback.message.edit_text(
        format_confirm_completion(reminder.task),
        reply_markup=get_reminder_confirm_done_keyboard(reminder_id),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem:cancel:"))
async def handle_reminder_cancel_done(callback: CallbackQuery) -> None:
    """Cancel completion and restore original reminder card."""
    reminder_id = int(callback.data.split(":")[2])
    reminder = get_reminder(reminder_id)
    if not reminder:
        await callback.answer("Reminder not found.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⏰ **Heads up:**\n\n**{reminder.task}**\n\nYou wanted this done right now.",
        reply_markup=get_reminder_action_keyboard(reminder_id),
        parse_mode="Markdown",
    )
    await callback.answer("Completion cancelled.")


@router.callback_query(F.data.startswith("rem:confirm:"))
async def handle_reminder_confirm_done(callback: CallbackQuery) -> None:
    """Confirm completion and show 60-second Undo button (PRD Section 18)."""
    reminder_id = int(callback.data.split(":")[2])
    reminder = complete_reminder(reminder_id)
    if not reminder:
        await callback.answer("Reminder not found.", show_alert=True)
        return

    await callback.message.edit_text(
        format_task_completed(reminder.task),
        reply_markup=get_reminder_undo_keyboard(reminder_id),
        parse_mode="Markdown",
    )
    await callback.answer("Marked as done! ✅")


@router.callback_query(F.data.startswith("rem:undo:"))
async def handle_reminder_undo(callback: CallbackQuery) -> None:
    """Handle Undo button with 60-second validity window (PRD Section 18)."""
    parts = callback.data.split(":")
    reminder_id = int(parts[2])
    done_timestamp = int(parts[3])

    elapsed = int(time.time()) - done_timestamp
    if elapsed > 60:
        await callback.answer("Undo expired (valid for 60 seconds).", show_alert=True)
        return

    reminder = undo_complete_reminder(reminder_id)
    if not reminder:
        await callback.answer("Could not restore task.", show_alert=True)
        return

    await callback.message.edit_text(
        format_task_restored(reminder.task),
        reply_markup=get_reminder_action_keyboard(reminder_id),
        parse_mode="Markdown",
    )
    await callback.answer("Task restored! ↩️")


@router.callback_query(F.data.startswith("rem:snooze:"))
async def handle_reminder_snooze(callback: CallbackQuery) -> None:
    """Snooze reminder by +30 minutes (PRD Section 19). Indefinite snooze allowed."""
    reminder_id = int(callback.data.split(":")[2])
    reminder = get_reminder(reminder_id)
    if not reminder or not callback.from_user:
        await callback.answer("Reminder not found.", show_alert=True)
        return

    user_tz = get_user_timezone(callback.from_user.id)
    now = datetime.now(user_tz)
    new_target = now + timedelta(minutes=30)
    new_display = TemporalEngine.format_display_time(new_target, now)

    new_job_id = scheduler_service.reschedule_reminder(reminder_id, new_target)
    snooze_reminder(reminder_id, new_target, new_display, new_job_id)

    await callback.message.edit_text(
        format_task_snoozed(reminder.task, new_display),
        parse_mode="Markdown",
    )
    await callback.answer("Snoozed for 30 minutes! ⏳")


# ---------------------------------------------------------------------------
# Vague-Time Clarification Callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("clrf:pick:"))
async def handle_clarification_pick(callback: CallbackQuery) -> None:
    """Handle user choosing one of the proposed clarification options."""
    parts = callback.data.split(":")
    clarification_id = int(parts[2])
    option_idx = int(parts[3])

    clarification = get_vague_clarification(clarification_id)
    if not clarification or not callback.from_user:
        await callback.answer("Clarification request not found.", show_alert=True)
        return

    options = clarification.options
    if option_idx >= len(options):
        await callback.answer("Invalid selection.", show_alert=True)
        return

    chosen_option = options[option_idx]
    if "no rush" in chosen_option.lower():
        resolve_vague_clarification(clarification_id, "dismissed_no_rush")
        await callback.message.edit_text(
            f"👍 Moved \"**{clarification.task}**\" to Clean Notes (no reminder set).",
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    user_tz = get_user_timezone(callback.from_user.id)
    now = datetime.now(user_tz)

    resolved_dt, display_time, conf = TemporalEngine.resolve_expression(chosen_option, now)
    if not resolved_dt:
        resolved_dt = now + timedelta(days=1)
        display_time = TemporalEngine.format_display_time(resolved_dt, now)
        conf = "inferred"

    # Create and arm real reminder
    new_rem = create_reminder(
        user_id=clarification.user_id,
        task=clarification.task,
        target_timestamp=resolved_dt,
        display_time=display_time or "Scheduled",
        confidence=conf,
        dump_id=clarification.dump_id,
    )
    job_id = scheduler_service.schedule_reminder(new_rem.id, resolved_dt)
    resolve_vague_clarification(clarification_id, "clarified")

    await callback.message.edit_text(
        f"🔔 **Armed:** \"**{clarification.task}**\"\n"
        f"Scheduled for **{display_time}**.\n\n"
        "I'll buzz you right here when it's time! 🫡",
        parse_mode="Markdown",
    )
    await callback.answer("Reminder scheduled! 🔔")


@router.callback_query(F.data.startswith("clrf:norush:"))
async def handle_clarification_no_rush(callback: CallbackQuery) -> None:
    """Handle 'No rush' choice — retain in Clean Notes without scheduling."""
    clarification_id = int(callback.data.split(":")[2])
    clarification = get_vague_clarification(clarification_id)
    if not clarification:
        await callback.answer("Clarification not found.", show_alert=True)
        return

    resolve_vague_clarification(clarification_id, "dismissed_no_rush")
    await callback.message.edit_text(
        f"👍 Moved \"**{clarification.task}**\" to Clean Notes (no reminder set).",
        parse_mode="Markdown",
    )
    await callback.answer("Moved to Clean Notes.")


# ---------------------------------------------------------------------------
# Voice & Audio Dump Handler
# ---------------------------------------------------------------------------

@router.message(F.voice | F.audio)
async def handle_voice_message(message: Message, bot: Bot) -> None:
    """Process incoming voice note or audio file according to PRD pipeline."""
    if not message.from_user:
        return

    user = get_or_create_user(message.from_user.id)
    user_tz = ZoneInfo(user.timezone)

    status_msg = await message.answer("🎧 _Listening to voice note..._", parse_mode="Markdown")

    file_id = message.voice.file_id if message.voice else message.audio.file_id
    raw_audio_path = None
    normalized_path = None

    try:
        raw_audio_path = await audio_ingestion.download_telegram_voice(bot, file_id)
        normalized_path = audio_ingestion.normalize_audio(raw_audio_path)

        # Transcribe using Whisper with Silero VAD
        from app.transcription.whisper import WhisperTranscriber

        transcriber = WhisperTranscriber()
        transcript, error_msg = transcriber.transcribe(normalized_path)

        if error_msg or not transcript:
            await status_msg.edit_text(error_msg or "I couldn't make that out — mind re-recording? 🎙️")
            return

        await status_msg.edit_text("🧠 _Organizing thoughts and scheduling..._", parse_mode="Markdown")

        # Extract structured items via LLM & deterministic temporal engine
        extracted, is_degraded = await llm_client.extract_dump(transcript, user_tz)

        # Save dump to database
        dump_rec = create_dump(
            user_id=message.from_user.id,
            raw_content=transcript,
            input_type="voice",
            summary=extracted.summary,
            clean_notes=extracted.clean_notes,
            action_items=extracted.action_items,
        )

        # Arm scheduled reminders
        now = datetime.now(user_tz)
        for r in extracted.scheduled_reminders:
            target_dt = datetime.fromisoformat(r.target_timestamp) if r.target_timestamp else (now + timedelta(hours=2))
            rem_rec = create_reminder(
                user_id=message.from_user.id,
                task=r.task,
                target_timestamp=target_dt,
                display_time=r.display_time or "Scheduled",
                confidence=r.confidence,
                dump_id=dump_rec.id,
            )
            scheduler_service.schedule_reminder(rem_rec.id, target_dt)

        # Arm vague-time clarifications
        for v in extracted.vague_reminders:
            clarify_at_dt = (
                datetime.fromisoformat(v.clarify_at)
                if v.clarify_at
                else (now + timedelta(seconds=1))
            )
            clrf_rec = create_vague_clarification(
                user_id=message.from_user.id,
                task=v.task,
                window=v.window,
                clarify_at=clarify_at_dt,
                options=v.options,
                dump_id=dump_rec.id,
            )
            scheduler_service.schedule_vague_clarification(clrf_rec.id, clarify_at_dt)

        card_text = format_response_card(extracted)
        await status_msg.edit_text(card_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing voice dump: {e}", exc_info=True)
        await status_msg.edit_text(
            "⚠️ An error occurred while processing your voice note. Please try again or send as text."
        )
    finally:
        # Guarantee privacy cleanup of audio files
        if raw_audio_path:
            audio_ingestion.cleanup_file(raw_audio_path)
        if normalized_path and normalized_path != raw_audio_path:
            audio_ingestion.cleanup_file(normalized_path)


# ---------------------------------------------------------------------------
# Text Dump Handler
# ---------------------------------------------------------------------------

@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Process incoming plain text brain dump (or timezone input if matching)."""
    if not message.text or not message.from_user:
        return

    text = text_ingestion.clean_text(message.text)
    user = get_or_create_user(message.from_user.id)
    user_tz = ZoneInfo(user.timezone)

    # Check if the user is typing a timezone
    if update_user_timezone(message.from_user.id, text):
        await message.answer(format_timezone_updated(text), parse_mode="Markdown")
        return

    status_msg = await message.answer("🧠 _Organizing thoughts and scheduling..._", parse_mode="Markdown")

    try:
        now = datetime.now(user_tz)
        extracted, is_degraded = await llm_client.extract_dump(text, user_tz, ref_now=now)

        dump_rec = create_dump(
            user_id=message.from_user.id,
            raw_content=text,
            input_type="text",
            summary=extracted.summary,
            clean_notes=extracted.clean_notes,
            action_items=extracted.action_items,
        )

        for r in extracted.scheduled_reminders:
            target_dt = datetime.fromisoformat(r.target_timestamp) if r.target_timestamp else (now + timedelta(hours=2))
            rem_rec = create_reminder(
                user_id=message.from_user.id,
                task=r.task,
                target_timestamp=target_dt,
                display_time=r.display_time or "Scheduled",
                confidence=r.confidence,
                dump_id=dump_rec.id,
            )
            scheduler_service.schedule_reminder(rem_rec.id, target_dt)

        for v in extracted.vague_reminders:
            clarify_at_dt = (
                datetime.fromisoformat(v.clarify_at)
                if v.clarify_at
                else (now + timedelta(seconds=1))
            )
            clrf_rec = create_vague_clarification(
                user_id=message.from_user.id,
                task=v.task,
                window=v.window,
                clarify_at=clarify_at_dt,
                options=v.options,
                dump_id=dump_rec.id,
            )
            scheduler_service.schedule_vague_clarification(clrf_rec.id, clarify_at_dt)

        card_text = format_response_card(extracted)
        await status_msg.edit_text(card_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing text dump: {e}", exc_info=True)
        await status_msg.edit_text(
            "⚠️ An error occurred while processing your message. Please try again."
        )
