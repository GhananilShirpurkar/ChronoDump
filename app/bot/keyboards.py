"""Inline keyboards and UI interactive components for ChronoDump Telegram Bot."""

import time
from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Return timezone selection buttons as defined in PRD Section 10.2."""
    keyboard = [
        [
            InlineKeyboardButton(text="UTC+5:30 — India", callback_data="tz:Asia/Kolkata"),
            InlineKeyboardButton(text="UTC+0 — GMT", callback_data="tz:UTC"),
        ],
        [
            InlineKeyboardButton(text="UTC-5 — ET", callback_data="tz:America/New_York"),
            InlineKeyboardButton(text="UTC+1 — CET", callback_data="tz:Europe/Berlin"),
        ],
        [
            InlineKeyboardButton(text="UTC+8 — Singapore/CST", callback_data="tz:Asia/Singapore"),
            InlineKeyboardButton(text="UTC-8 — PT", callback_data="tz:America/Los_Angeles"),
        ],
        [
            InlineKeyboardButton(text="Other / Type custom timezone", callback_data="tz:custom"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_action_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return [ ✅ Done ] and [ ⏳ +30 min ] buttons for active reminder."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"rem:done:{reminder_id}"),
            InlineKeyboardButton(text="⏳ +30 min", callback_data=f"rem:snooze:{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_confirm_done_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return confirmation buttons before completing a task."""
    keyboard = [
        [
            InlineKeyboardButton(text="Confirm ✅", callback_data=f"rem:confirm:{reminder_id}"),
            InlineKeyboardButton(text="Cancel", callback_data=f"rem:cancel:{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_undo_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return [ ↩️ Undo ] button timestamped for 60-second expiration."""
    now_ts = int(time.time())
    keyboard = [
        [
            InlineKeyboardButton(text="↩️ Undo", callback_data=f"rem:undo:{reminder_id}:{now_ts}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_clarification_keyboard(clarification_id: int, options: List[str]) -> InlineKeyboardMarkup:
    """Return dynamic option buttons for vague deadline disambiguation."""
    keyboard = []
    # Two options per row
    row = []
    for idx, opt in enumerate(options):
        btn = InlineKeyboardButton(text=opt, callback_data=f"clrf:pick:{clarification_id}:{idx}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Always provide 'No rush' option if not already present
    if not any("no rush" in o.lower() for o in options):
        keyboard.append([InlineKeyboardButton(text="No rush", callback_data=f"clrf:norush:{clarification_id}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_degraded_arm_keyboard(dump_id: int) -> InlineKeyboardMarkup:
    """Return buttons for degraded fallback response (PRD Section 20 Failure 2)."""
    keyboard = [
        [
            InlineKeyboardButton(text="🔔 Arm these", callback_data=f"deg:arm:{dump_id}"),
            InlineKeyboardButton(text="✏️ Ignore", callback_data=f"deg:ignore:{dump_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
