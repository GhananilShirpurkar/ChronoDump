"""Message formatting and templates matching ChronoDump PRD specifications."""

from datetime import datetime
from typing import List, Optional
from app.intelligence.schema import ExtractedDump


def format_start_welcome(user_id: int) -> str:
    """Return welcome message on /start."""
    return (
        "👋 **Welcome to ChronoDump!**\n\n"
        "Turn raw audio chaos into structured plans and auto-armed reminders.\n\n"
        "Just send or forward me a voice note or plain text message whenever a thought hits you.\n\n"
        "To get started, please select your timezone so all reminders trigger at the right moment:"
    )


def format_unauthorized_rejection() -> str:
    """Return security rejection message for unauthorized users."""
    return "🔒 **Access Restricted**\n\nThis ChronoDump instance is configured for single-user personal use only."


def format_timezone_prompt(current_tz: Optional[str] = None) -> str:
    """Format timezone selection prompt."""
    status = f"\nCurrently set to: `{current_tz}`" if current_tz else ""
    return f"🌍 **What timezone are you in?**{status}\n\nSelect an option below or choose custom to type your offset:"


def format_timezone_updated(new_tz: str) -> str:
    """Confirmation message after setting timezone."""
    return f"✅ Timezone updated to `{new_tz}`.\n\nYou're all set! Send me a voice note or text dump whenever you're ready."


def format_response_card(dump: ExtractedDump) -> str:
    """
    Format the Telegram response card exactly according to PRD Section 15.
    """
    sections: List[str] = ["⚡ **Sorted. Here's your dump:**"]

    # 1. Clean Notes
    if dump.clean_notes:
        notes_lines = ["\n📋 **CLEAN NOTES**"]
        for note in dump.clean_notes:
            notes_lines.append(f"• {note}")
        sections.append("\n".join(notes_lines))

    # 2. Action Items
    if dump.action_items:
        action_lines = ["\n✅ **ACTION ITEMS**"]
        for item in dump.action_items:
            action_lines.append(f"◻️ {item}")
        sections.append("\n".join(action_lines))

    # 3. Armed Reminders
    if dump.scheduled_reminders:
        reminder_lines = ["\n⏰ **ARMED REMINDERS**"]
        for r in dump.scheduled_reminders:
            disp = r.display_time or "Scheduled"
            reminder_lines.append(f"🔔 {disp} — {r.task}")
        sections.append("\n".join(reminder_lines))

    # 4. Needs a Nudge / Vague Reminders
    if dump.vague_reminders:
        vague_lines = ["\n🔍 **NEEDS A NUDGE**"]
        for v in dump.vague_reminders:
            opts_summary = " or ".join(v.options[:2]) if v.options else "when to remind you"
            vague_lines.append(f"◻️ {v.task}\n   _I'll ask you soon: {opts_summary}?_")
        sections.append("\n".join(vague_lines))

    # Check for empty state (Failure 4 — No tasks/deadlines)
    has_tasks = bool(dump.scheduled_reminders or dump.vague_reminders or dump.action_items)
    if not has_tasks and not dump.clean_notes:
        return "⚡ **Sorted.**\n\nNo tasks or context detected in dump."

    if not has_tasks:
        sections.append("\n_No deadlines heard._")
    else:
        sections.append("\n_I'll buzz you right here when it's time. 🫡_")

    return "\n".join(sections)


def format_reminder_alert(task: str) -> str:
    """Format reminder alert when trigger time is reached (PRD Section 17)."""
    return (
        "⏰ **Heads up:**\n\n"
        f"**{task}**\n\n"
        "You wanted this done right now."
    )


def format_confirm_completion(task: str) -> str:
    """Format confirmation prompt before marking task complete (PRD Section 18)."""
    return (
        f"Mark this task as complete?\n\n"
        f"**{task}**"
    )


def format_task_completed(task: str) -> str:
    """Format task marked complete confirmation."""
    return (
        "✅ **Done.**\n\n"
        f"_{task}_ marked complete."
    )


def format_task_snoozed(task: str, display_time: str) -> str:
    """Format snooze confirmation (PRD Section 19)."""
    return (
        "⏳ **Snoozed for 30 minutes:**\n\n"
        f"**{task}**\n\n"
        f"I'll buzz you at {display_time}."
    )


def format_task_restored(task: str) -> str:
    """Format task restored from undo."""
    return (
        "↩️ **Task restored:**\n\n"
        f"**{task}**\n\n"
        "You can mark it done or snooze whenever you are ready."
    )


def format_clarification_prompt(task: str, window: str) -> str:
    """Format vague deadline clarification prompt (PRD Section 12)."""
    window_label = window.replace("_", " ")
    return (
        "🔍 **Needs clarification:**\n\n"
        f"**{task}**\n\n"
        f"You mentioned this for {window_label}. When should I remind you?"
    )


def format_today_agenda(now: datetime, reminders: list, actions: list, notes_count: int) -> str:
    """Format daily briefing for /today."""
    date_str = now.strftime("%A, %b %-d")
    lines = [f"📅 **Today's Agenda — {date_str}**\n"]

    if reminders:
        lines.append(f"⏰ **ARMED FOR TODAY ({len(reminders)})**")
        for r in reminders:
            status_emoji = "⏳" if r.status == "snoozed" else "🔔"
            lines.append(f"{status_emoji} `{r.display_time}` — **{r.task}**")
    else:
        lines.append("⏰ **ARMED FOR TODAY**\n_No reminders scheduled for today!_")

    lines.append("")
    if actions:
        lines.append(f"✅ **OPEN ACTION ITEMS ({len(actions)})**")
        for act in actions[:8]:
            lines.append(f"◻️ {act['action']}")
        if len(actions) > 8:
            lines.append(f"_...and {len(actions) - 8} more_")
    else:
        lines.append("✅ **OPEN ACTION ITEMS**\n_No pending action items._")

    lines.append(f"\n💡 *Total Clean Notes stored: {notes_count}* (type /notes to browse)")
    return "\n".join(lines)


def format_queue_header(count: int) -> str:
    """Header for /queue list."""
    if count == 0:
        return "📭 **Reminder Queue is empty!**\n\nSend a voice note or text dump to arm reminders."
    return f"📋 **Active Reminder Queue ({count} pending):**\n\nManage each reminder below:"


def format_notes_view(notes: list) -> str:
    """Format /notes repository view."""
    if not notes:
        return "📋 **Your Clean Notes Repository**\n\n_No notes stored yet! Send a voice dump with any thoughts, ideas, or context._"

    lines = ["📋 **Your Clean Notes Repository**\n"]
    for item in notes[:15]:
        created_str = item["created_at"].strftime("%b %-d") if item.get("created_at") else ""
        date_badge = f" *({created_str})*" if created_str else ""
        lines.append(f"• {item['note']}{date_badge}")

    lines.append("\n💡 _Notes with no deadlines are preserved here so your brain dump stays organized._")
    return "\n".join(lines)


def format_focus_status(focus_until: Optional[datetime], now: datetime) -> str:
    """Format /focus status message."""
    if focus_until and focus_until > now:
        remaining_mins = max(1, int((focus_until - now).total_seconds() / 60))
        time_str = focus_until.strftime("%I:%M %p")
        return (
            "🧘 **Focus Mode is ACTIVE**\n\n"
            f"Alerts are paused until **{time_str}** (~{remaining_mins} min remaining).\n"
            "Any reminders that fire during this time will be politely delayed until your focus block ends.\n\n"
            "Choose a quick duration below to extend or turn it off:"
        )
    return (
        "🧘 **Focus Mode**\n\n"
        "Need uninterrupted deep work? Focus Mode temporarily delays incoming reminders so you can concentrate without distractions.\n\n"
        "Select a duration to begin:"
    )


def format_stats_view(stats: dict) -> str:
    """Format system and local AI observability card for /stats."""
    return (
        "📊 **ChronoDump System & AI Stats**\n\n"
        "🤖 **Local AI Infrastructure**\n"
        f"• **Speech-to-Text:** `faster-whisper` (`{stats['whisper_model']}` / `{stats['whisper_compute']}` on `{stats['whisper_device']}`)\n"
        f"• **VAD Filter:** `Silero VAD (500ms min silence)`\n"
        f"• **Reasoning LLM:** `Ollama` (`{stats['ollama_model']}`)\n"
        f"• **Endpoint:** `{stats['ollama_url']}`\n\n"
        "📈 **Your Activity**\n"
        f"• **Brain Dumps Processed:** `{stats['dump_count']}`\n"
        f"• **Active Reminders:** `{stats['active_reminders']}`\n"
        f"• **Completed Reminders:** `{stats['completed_reminders']}`\n"
        f"• **Total Reminders Logged:** `{stats['total_reminders']}`\n\n"
        "💾 **Storage & Environment**\n"
        f"• **Database Size:** `{stats['db_size_kb']} KB` (SQLite)\n"
        f"• **Scheduler Engine:** `APScheduler + SQLite JobStore`\n"
        f"• **Active Timezone:** `{stats['timezone']}`"
    )
