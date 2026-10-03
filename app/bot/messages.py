"""Message formatting and UI presentation layer for ChronoDump Telegram Bot.

Implements the ChronoDump Design System:
- Executive summary cards
- Urgent actionable alerts
- Focused decision prompts
- Lightweight confirmations
- Clean observability dashboards
"""

from datetime import datetime
from typing import List, Optional
from app.bot.design import (
    BRAND_HEADER,
    DIVIDER,
    THIN_DIVIDER,
    build_decision_card,
    build_feedback_banner,
    build_urgent_alert,
    render_action_item,
    render_note_item,
    render_reminder_item,
    render_section_header,
    render_stats_footer,
    render_vague_item,
)
from app.intelligence.schema import ExtractedDump


# ---------------------------------------------------------------------------
# 1. Onboarding & Security
# ---------------------------------------------------------------------------

def format_start_welcome(user_id: int) -> str:
    """Return welcome message on /start."""
    return (
        f"{BRAND_HEADER}\n"
        f"{DIVIDER}\n"
        "_Turn raw audio chaos into structured plans and auto-armed reminders._\n\n"
        "🎯 **How it works:**\n"
        "• Drop or forward a voice note or messy brain dump whenever thoughts hit you.\n"
        "• ChronoDump distills context, extracts action items, and calculates relative deadlines.\n"
        "• Reminders are **automatically armed** — zero date-pickers or manual forms!\n\n"
        "🌍 To get started, select your active timezone below:"
    )


def format_unauthorized_rejection() -> str:
    """Return security rejection message for unauthorized users."""
    return (
        "🔒 **Access Restricted**\n"
        f"{DIVIDER}\n"
        "This ChronoDump instance is configured for single-user personal privacy only."
    )


# ---------------------------------------------------------------------------
# 2. Timezone Configuration
# ---------------------------------------------------------------------------

def format_timezone_prompt(current_tz: Optional[str] = None) -> str:
    """Format timezone selection prompt."""
    status = f"\nCurrently set to: `{current_tz}`" if current_tz else ""
    return (
        "🌍 **TIMEZONE CONFIGURATION**\n"
        f"{DIVIDER}{status}\n\n"
        "Select your active timezone below or choose custom to enter your offset:"
    )


def format_timezone_updated(new_tz: str) -> str:
    """Confirmation message after setting timezone."""
    return (
        "✅ **Timezone Updated**\n"
        f"{DIVIDER}\n"
        f"Active timezone set to `{new_tz}`.\n\n"
        "_Ready for your next brain dump! Speak or type anytime. 🤙_"
    )


def format_timezone_custom_prompt() -> str:
    """Prompt for typing a custom timezone string."""
    return (
        "🌍 **Custom Timezone**\n"
        f"{DIVIDER}\n"
        "Please reply with your standard IANA timezone (e.g. `America/Chicago`, `Europe/London`, `Asia/Tokyo`) or UTC offset (e.g. `+05:30`, `-04:00`):"
    )


# ---------------------------------------------------------------------------
# 3. Processed Dump ("Summary Card")
# ---------------------------------------------------------------------------

def format_response_card(dump: ExtractedDump) -> str:
    """
    Format the Telegram response card with clean visual hierarchy, summary quote,
    and polished badges (PRD Section 15).
    """
    header = "⚡ **CHRONODUMP**"
    if dump.summary and dump.summary.strip():
        header += f"\n{DIVIDER}\n💬 _\"{dump.summary.strip()}\"_\n{DIVIDER}"
    else:
        header += f"\n{DIVIDER}"

    sections: List[str] = [header]

    # 1. Clean Notes
    if dump.clean_notes:
        notes_lines = [f"\n📝 **CLEAN NOTES**"]
        for note in dump.clean_notes:
            notes_lines.append(render_note_item(note))
        sections.append("\n".join(notes_lines))

    # 2. Action Items (Undated)
    if dump.action_items:
        action_lines = [f"\n🎯 **ACTION ITEMS**"]
        for item in dump.action_items:
            action_lines.append(render_action_item(item))
        sections.append("\n".join(action_lines))

    # 3. Armed Reminders (Time-critical)
    if dump.scheduled_reminders:
        reminder_lines = [f"\n⏰ **ARMED REMINDERS**"]
        for r in dump.scheduled_reminders:
            disp = r.display_time or "Scheduled"
            reminder_lines.append(render_reminder_item(disp, r.task))
        sections.append("\n".join(reminder_lines))

    # 4. Needs a Nudge / Vague Reminders
    if dump.vague_reminders:
        vague_lines = [f"\n🔍 **NEEDS A NUDGE**"]
        for v in dump.vague_reminders:
            vague_lines.append(render_vague_item(v.task, v.options or []))
        sections.append("\n".join(vague_lines))

    # Check for empty state
    has_tasks = bool(dump.scheduled_reminders or dump.vague_reminders or dump.action_items)
    if not has_tasks and not dump.clean_notes:
        return f"{BRAND_HEADER}\n{DIVIDER}\nNo tasks, deadlines, or notes detected in this input."

    if not has_tasks:
        sections.append(f"\n{DIVIDER}\n_No deadlines heard — notes saved to repository._")
    else:
        # Summary footer pill
        footer = render_stats_footer(
            notes_cnt=len(dump.clean_notes),
            actions_cnt=len(dump.action_items),
            reminders_cnt=len(dump.scheduled_reminders),
        )
        sections.append(f"\n{footer}")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# 4. Reminder Alerts & Interactivity
# ---------------------------------------------------------------------------

def format_reminder_alert(task: str) -> str:
    """Format reminder alert when trigger time is reached (PRD Section 17)."""
    return build_urgent_alert(
        title="⏰ **ACTION REQUIRED**",
        task=task,
        prompt="You scheduled this for right now.",
    )


def format_confirm_completion(task: str) -> str:
    """Format confirmation prompt before marking task complete (PRD Section 18)."""
    return (
        "Mark task as complete?\n"
        f"{DIVIDER}\n"
        f"📌 **{task}**"
    )


def format_task_completed(task: str) -> str:
    """Format task marked complete confirmation."""
    return build_feedback_banner(
        status_icon="✓",
        title="Done.",
        detail=f"_{task}_ marked complete.\n\n_Undo available for 60 seconds._",
    )


def format_task_snoozed(task: str, display_time: str) -> str:
    """Format snooze confirmation (PRD Section 19)."""
    return build_feedback_banner(
        status_icon="⏳",
        title="Snoozed · 30 min",
        detail=f"📌 **{task}**\n\n🔔 Next alert at: `{display_time}`\n_Held quietly until then._",
    )


def format_task_restored(task: str) -> str:
    """Format task restored from undo."""
    return build_feedback_banner(
        status_icon="↩️",
        title="Task Restored",
        detail=f"📌 **{task}**\n\n_Back on your active radar. Mark done or snooze whenever ready._",
    )


def format_clarification_prompt(task: str, window: str) -> str:
    """Format vague deadline clarification prompt (PRD Section 12)."""
    window_label = window.replace("_", " ")
    return build_decision_card(
        title="🔍 **NEEDS CLARIFICATION**",
        task=task,
        question=f"You mentioned this for _{window_label}_. When would you like to be alerted?",
    )


def format_clarification_resolved(task: str, display_time: str) -> str:
    """Format confirmation after resolving a vague clarification."""
    return build_feedback_banner(
        status_icon="✓",
        title="Reminder Scheduled",
        detail=f"📌 **{task}**\n\n🔔 Alert armed for: `{display_time}`",
    )


def format_clarification_dismissed(task: str) -> str:
    """Format feedback when vague reminder is moved to Clean Notes without a timer."""
    return build_feedback_banner(
        status_icon="📝",
        title="Saved to Notes",
        detail=f"📌 **{task}**\n\n_Moved to Clean Notes with no timer attached._",
    )


# ---------------------------------------------------------------------------
# 5. Slash Command Views (/today, /queue, /notes, /focus, /stats, /help, /export)
# ---------------------------------------------------------------------------

def format_today_agenda(now: datetime, reminders: list, actions: list, notes_count: int) -> str:
    """Format daily briefing for /today."""
    date_str = now.strftime("%A, %b %-d")
    lines = [
        f"📅 **TODAY'S RADAR** · _{date_str}_\n"
        f"{DIVIDER}"
    ]

    if reminders:
        lines.append(f"\n⏰ **ARMED FOR TODAY ({len(reminders)})**")
        for r in reminders:
            status_val = getattr(r, "status", "pending")
            status_emoji = "⏳" if status_val == "snoozed" else "🔔"
            lines.append(f"• {status_emoji} `{r.display_time}` — **{r.task}**")
    else:
        lines.append("\n⏰ **ARMED FOR TODAY**\n_No reminders scheduled for today! Enjoy your flow._")

    lines.append("")
    if actions:
        lines.append(f"🎯 **OPEN ACTION ITEMS ({len(actions)})**")
        for act in actions[:8]:
            lines.append(f"• ◻️ {act['action']}")
        if len(actions) > 8:
            lines.append(f"_...and {len(actions) - 8} more_")
    else:
        lines.append("🎯 **OPEN ACTION ITEMS**\n_No pending action items._")

    lines.append(
        f"\n{DIVIDER}\n"
        f"💡 _{notes_count} clean notes in storage · Browse with /notes or manage /queue_"
    )
    return "\n".join(lines)


def format_queue_header(count: int) -> str:
    """Header for /queue list."""
    if count == 0:
        return (
            "📭 **Reminder Queue Empty**\n"
            f"{DIVIDER}\n"
            "No active reminders scheduled. Send a voice note or text dump to auto-arm reminders."
        )
    return (
        f"📋 **ACTIVE REMINDER RADAR** ({count} pending)\n"
        f"{DIVIDER}\n"
        "Manage your upcoming alerts below:"
    )


def format_queue_item_card(task: str, display_time: str, status: str) -> str:
    """Individual card for a reminder inside /queue."""
    status_icon = "⏳" if status == "snoozed" else "🔔"
    return (
        f"{status_icon} **{task}**\n"
        f"• ⏰ Scheduled: `{display_time}`\n"
        f"• 📌 Status: `{status.upper()}`"
    )


def format_notes_view(notes: list) -> str:
    """Format /notes repository view."""
    if not notes:
        return (
            "📝 **CLEAN NOTES REPOSITORY**\n"
            f"{DIVIDER}\n"
            "_No notes stored yet! Send a voice dump with any thoughts, ideas, or context._"
        )

    lines = [
        "📝 **CLEAN NOTES REPOSITORY**\n"
        f"{DIVIDER}"
    ]
    for item in notes[:15]:
        created_str = item["created_at"].strftime("%b %-d") if item.get("created_at") else ""
        date_badge = f" *({created_str})*" if created_str else ""
        lines.append(f"• {item['note']}{date_badge}")

    lines.append(
        f"\n{DIVIDER}\n"
        "💡 _Context and ideas without deadlines are preserved here for reference._"
    )
    return "\n".join(lines)


def format_focus_status(focus_until: Optional[datetime], now: datetime) -> str:
    """Format /focus status message."""
    if focus_until and focus_until > now:
        remaining_mins = max(1, int((focus_until - now).total_seconds() / 60))
        time_str = focus_until.strftime("%I:%M %p")
        return (
            "🧘 **DEEP FOCUS ACTIVE**\n"
            f"{DIVIDER}\n"
            f"🛡️ _Alerts paused until **{time_str}** (~{remaining_mins} min remaining)_\n\n"
            "Any reminders due during this session will be queued quietly until you emerge.\n\n"
            "Select an option below to extend or exit:"
        )
    return (
        "🧘 **DEEP FOCUS SANCTUARY**\n"
        f"{DIVIDER}\n"
        "Need uninterrupted flow? Focus Mode pauses reminder notifications so you can immerse yourself in deep work. Reminders due during this block will be queued politely until you emerge.\n\n"
        "⏱️ **Select your focus window:**"
    )


def format_focus_ended() -> str:
    """Message when focus mode is turned off."""
    return build_feedback_banner(
        status_icon="🛑",
        title="Focus Mode Ended",
        detail="All notifications and incoming reminders restored.",
    )


def format_stats_view(stats: dict) -> str:
    """Format system and local AI observability card for /stats."""
    return (
        "📊 **CHRONODUMP SYSTEM & AI STATS**\n"
        f"{DIVIDER}\n"
        "🤖 **Local AI Infrastructure**\n"
        f"• Speech Engine: `faster-whisper` (`{stats['whisper_model']}` / `{stats['whisper_compute']}` on `{stats['whisper_device']}`)\n"
        f"• Noise Suppression: `Silero VAD (500ms speech boundary)`\n"
        f"• Reasoning LLM: `Ollama` (`{stats['ollama_model']}`)\n"
        f"• Model Endpoint: `{stats['ollama_url']}`\n\n"
        "📈 **Throughput & Activity**\n"
        f"• Brain Dumps Processed: `{stats['dump_count']}`\n"
        f"• Active Reminders: `{stats['active_reminders']}`\n"
        f"• Completed Reminders: `{stats['completed_reminders']}`\n"
        f"• Total Reminders Logged: `{stats['total_reminders']}`\n\n"
        "💾 **Storage & Environment**\n"
        f"• Database Size: `{stats['db_size_kb']} KB` (SQLite)\n"
        f"• Scheduler Engine: `APScheduler + SQLite JobStore`\n"
        f"• Active Timezone: `{stats['timezone']}`"
    )


def format_help() -> str:
    """Format /help command directory."""
    return (
        "⚡ **CHRONODUMP COMMAND CENTER**\n"
        f"{DIVIDER}\n"
        "_Turn raw audio chaos into structured plans and auto-armed reminders._\n\n"
        "🎯 **Available Commands:**\n"
        "• `/today` — Today's radar, armed reminders & open action items\n"
        "• `/queue` — View and manage all scheduled reminders\n"
        "• `/notes` — Browse your clean notes & context repository\n"
        "• `/focus` — Pause alerts for deep work (`/focus 1h` or tap buttons)\n"
        "• `/stats` — Local AI engine specs & activity metrics\n"
        "• `/export` — Export all notes & tasks as a Markdown file\n"
        "• `/timezone` — Check or change your active timezone\n"
        "• `/help` — Display this command directory\n\n"
        f"{DIVIDER}\n"
        "💡 _Pro-Tip: Just drop a voice note or messy text dump anytime. Reminders are armed automatically!_"
    )


def format_export_caption() -> str:
    """Caption for /export document."""
    return (
        "📦 **ChronoDump Markdown Export**\n"
        f"{DIVIDER}\n"
        "Ready to drop into Obsidian, Notion, or Apple Notes."
    )


# ---------------------------------------------------------------------------
# 6. Processing & Status Indicators
# ---------------------------------------------------------------------------

def format_transcribing_voice() -> str:
    """Indicator when voice audio is being ingested and transcribed."""
    return (
        "🎙️ **Transcribing Audio**\n"
        "_Filtering background noise with Silero VAD..._"
    )


def format_synthesizing_dump() -> str:
    """Indicator when LLM is structuring the brain dump."""
    return (
        "⚡ **Synthesizing Intelligence**\n"
        "_Resolving temporal deadlines & structuring tasks..._"
    )


def format_analyzing_text() -> str:
    """Indicator when text dump is being parsed."""
    return (
        "⚡ **Processing Dump**\n"
        "_Extracting action items & scheduling timers..._"
    )


# ---------------------------------------------------------------------------
# 7. Error & Exception Presentations
# ---------------------------------------------------------------------------

def format_audio_error(detail: Optional[str] = None) -> str:
    """Friendly error message when voice audio cannot be parsed."""
    msg = detail or "I couldn't clearly decipher speech in that audio note."
    return (
        "⚠️ **Audio Unclear**\n"
        f"{DIVIDER}\n"
        f"{msg}\n\n"
        "_Please try speaking slightly closer to the mic or send as text._"
    )


def format_generic_error(detail: Optional[str] = None) -> str:
    """Graceful error message for unexpected failures."""
    msg = detail or "An unexpected issue occurred while parsing this message."
    return (
        "⚠️ **Processing Interrupted**\n"
        f"{DIVIDER}\n"
        f"{msg}\n\n"
        "_Your data is safe — please retry or send as text._"
    )


# ---------------------------------------------------------------------------
# 8. Queue Inline Action Confirmations
# ---------------------------------------------------------------------------

def format_queue_action_done(task: str) -> str:
    """Feedback when marking done from queue."""
    return f"✓ Marked **{task}** complete."


def format_queue_action_snoozed(task: str, display_time: str) -> str:
    """Feedback when snoozing from queue."""
    return f"⏳ Snoozed **{task}** for 30 minutes (until {display_time})."


def format_queue_action_cancelled(task: str) -> str:
    """Feedback when cancelling from queue."""
    return f"❌ Cancelled reminder: **{task}**"
