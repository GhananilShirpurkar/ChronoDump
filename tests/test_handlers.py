"""Unit tests for bot messages formatting, response cards, and keyboards."""

from app.bot.keyboards import (
    get_clarification_keyboard,
    get_reminder_action_keyboard,
    get_reminder_confirm_done_keyboard,
    get_reminder_undo_keyboard,
    get_timezone_keyboard,
)
from app.bot.messages import (
    format_clarification_prompt,
    format_confirm_completion,
    format_reminder_alert,
    format_response_card,
    format_task_completed,
    format_task_snoozed,
    format_timezone_updated,
    format_unauthorized_rejection,
)
from app.intelligence.schema import ExtractedDump, ScheduledReminder, VagueReminder


def test_response_card_formatting_full_sample() -> None:
    """Verify formatting matches ChronoDump Design System."""
    dump = ExtractedDump(
        summary="Reading, report, water, and laundry",
        clean_notes=["Chapter 4 contains the material needed"],
        action_items=[],
        scheduled_reminders=[
            ScheduledReminder(
                task="Read Chapter 4",
                display_time="Tonight @ 10:00 PM",
                confidence="exact",
            ),
            ScheduledReminder(
                task="Submit Final Project Report",
                display_time="Jan 3 @ 11:59 PM",
                confidence="inferred",
            ),
            ScheduledReminder(
                task="Drink water 🚰",
                display_time="In 2 minutes",
                confidence="exact",
            ),
        ],
        vague_reminders=[
            VagueReminder(
                task="Pick up laundry",
                window="this_weekend",
                options=["Saturday", "Sunday"],
            )
        ],
    )

    card = format_response_card(dump)
    assert "⚡ **CHRONODUMP**" in card
    assert "📝 **CLEAN NOTES**" in card
    assert "• Chapter 4 contains the material needed" in card
    assert "⏰ **ARMED REMINDERS**" in card
    assert "Tonight @ 10:00 PM" in card
    assert "Read Chapter 4" in card
    assert "Submit Final Project Report" in card
    assert "Drink water 🚰" in card
    assert "🔍 **NEEDS A NUDGE**" in card
    assert "Pick up laundry" in card
    assert "reminders armed" in card


def test_response_card_no_deadlines() -> None:
    dump = ExtractedDump(
        summary="Just notes",
        clean_notes=["Remember to buy groceries"],
        action_items=[],
        scheduled_reminders=[],
        vague_reminders=[],
    )
    card = format_response_card(dump)
    assert "No deadlines heard — notes saved to repository." in card


def test_reminder_alert_message() -> None:
    msg = format_reminder_alert("Read Chapter 4")
    assert "⏰ **ACTION REQUIRED**" in msg
    assert "**Read Chapter 4**" in msg
    assert "You scheduled this for right now." in msg


def test_keyboards_structure() -> None:
    tz_kb = get_timezone_keyboard()
    assert len(tz_kb.inline_keyboard) >= 3

    rem_kb = get_reminder_action_keyboard(42)
    assert len(rem_kb.inline_keyboard[0]) == 2
    assert rem_kb.inline_keyboard[0][0].text == "✓ Done"
    assert rem_kb.inline_keyboard[0][1].text == "+30 min"

    confirm_kb = get_reminder_confirm_done_keyboard(42)
    assert confirm_kb.inline_keyboard[0][0].text == "Confirm ✓"
    assert confirm_kb.inline_keyboard[0][1].text == "Cancel"

    undo_kb = get_reminder_undo_keyboard(42)
    assert undo_kb.inline_keyboard[0][0].text == "↩ Undo"
    assert "rem:undo:42:" in undo_kb.inline_keyboard[0][0].callback_data

    clrf_kb = get_clarification_keyboard(10, ["Saturday 9 AM", "Sunday 9 AM"])
    assert any("Saturday" in b.text for row in clrf_kb.inline_keyboard for b in row)
    assert any("No rush" in b.text for row in clrf_kb.inline_keyboard for b in row)
