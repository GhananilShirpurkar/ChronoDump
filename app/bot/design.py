"""ChronoDump Telegram UI Design System and presentation primitives.

Provides a unified visual language:
- Consistent Unicode divider rails
- Brand headers & status badges
- Structured card builders for dumps, reminders, decisions, and system alerts
- Strict Telegram Markdown formatting safety
"""

from typing import List, Optional


# ---------------------------------------------------------------------------
# Visual Tokens
# ---------------------------------------------------------------------------

# Rail divider: 20 characters provides optimal balance on mobile and desktop Telegram
DIVIDER = "━━━━━━━━━━━━━━━━━━━━"
THIN_DIVIDER = "────────────────────"

# Brand header
BRAND_HEADER = "⚡ **CHRONODUMP**"


# ---------------------------------------------------------------------------
# Core Item Builders
# ---------------------------------------------------------------------------

def render_section_header(title: str, count: Optional[int] = None) -> str:
    """Format section title with optional count badge."""
    count_badge = f" ({count})" if count is not None else ""
    return f"{title}{count_badge}"


def render_note_item(note: str, timestamp_str: Optional[str] = None) -> str:
    """Render a single context note with clean bullet."""
    date_badge = f" _({timestamp_str})_" if timestamp_str else ""
    return f"• {note}{date_badge}"


def render_action_item(task: str) -> str:
    """Render an undated action item with modern checkbox."""
    return f"• ◻️ {task}"


def render_reminder_item(display_time: str, task: str, status: Optional[str] = None) -> str:
    """Render a time-armed reminder with monospace timestamp and directional icon."""
    status_icon = "⏳" if status == "snoozed" else "🔔"
    return f"• {status_icon} `{display_time}` — **{task}**"


def render_vague_item(task: str, options: List[str]) -> str:
    """Render a vague-time clarification item with proposed options."""
    opts_summary = " · ".join(options[:2]) if options else "options"
    return f"• ◻️ **{task}**\n  └ 💬 _\"{opts_summary}?\"_"


def render_stats_footer(notes_cnt: int, actions_cnt: int, reminders_cnt: int) -> str:
    """Render compact summary status line at the bottom of a response card."""
    parts = []
    if reminders_cnt > 0:
        plural = "reminder" if reminders_cnt == 1 else "reminders"
        parts.append(f"{reminders_cnt} {plural} armed")
    if actions_cnt > 0:
        plural = "action" if actions_cnt == 1 else "actions"
        parts.append(f"{actions_cnt} {plural}")
    if notes_cnt > 0:
        plural = "note" if notes_cnt == 1 else "notes"
        parts.append(f"{notes_cnt} {plural}")

    summary_str = " · ".join(parts) if parts else "Saved"
    return f"{DIVIDER}\n🔔 _{summary_str} · Type /today for radar_"


# ---------------------------------------------------------------------------
# Card Templates
# ---------------------------------------------------------------------------

def build_card(
    header: str,
    sections: List[str],
    footer: Optional[str] = None,
    divider: str = DIVIDER,
) -> str:
    """Compose a multi-section Telegram card with consistent rail dividers."""
    body_blocks = [header, divider]
    for sec in sections:
        if sec and sec.strip():
            body_blocks.append(sec.strip())

    if footer:
        body_blocks.append(footer.strip())

    return "\n\n".join(body_blocks)


def build_urgent_alert(title: str, task: str, prompt: str) -> str:
    """Card for immediate action required (e.g. reminder fired)."""
    return (
        f"{title}\n"
        f"{DIVIDER}\n"
        f"📌 **{task}**\n\n"
        f"_{prompt}_"
    )


def build_decision_card(title: str, task: str, question: str) -> str:
    """Card focusing user attention on a decision (e.g. vague clarification)."""
    return (
        f"{title}\n"
        f"{DIVIDER}\n"
        f"📌 **{task}**\n\n"
        f"{question}"
    )


def build_feedback_banner(status_icon: str, title: str, detail: Optional[str] = None) -> str:
    """Lightweight feedback banner (e.g. Done, Snoozed, Restored)."""
    text = (
        f"{status_icon} **{title}**\n"
        f"{DIVIDER}"
    )
    if detail:
        text += f"\n{detail}"
    return text
