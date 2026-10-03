"""Message formatting and templates matching ChronoDump PRD specifications."""

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
