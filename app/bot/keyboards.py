"""Inline keyboards and UI interactive components for ChronoDump Telegram Bot."""

import time
from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Return timezone selection buttons with clean, modern abbreviations."""
    keyboard = [
        [
            InlineKeyboardButton(text="IST · UTC+5:30", callback_data="tz:Asia/Kolkata"),
            InlineKeyboardButton(text="GMT · UTC+0", callback_data="tz:UTC"),
        ],
        [
            InlineKeyboardButton(text="ET · UTC-5", callback_data="tz:America/New_York"),
            InlineKeyboardButton(text="CET · UTC+1", callback_data="tz:Europe/Berlin"),
        ],
        [
            InlineKeyboardButton(text="SGT · UTC+8", callback_data="tz:Asia/Singapore"),
            InlineKeyboardButton(text="PT · UTC-8", callback_data="tz:America/Los_Angeles"),
        ],
        [
            InlineKeyboardButton(text="Custom Timezone...", callback_data="tz:custom"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_action_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return [ ✓ Done ] and [ +30 min ] buttons for active reminder."""
    keyboard = [
        [
            InlineKeyboardButton(text="✓ Done", callback_data=f"rem:done:{reminder_id}"),
            InlineKeyboardButton(text="+30 min", callback_data=f"rem:snooze:{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_confirm_done_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return confirmation buttons before completing a task."""
    keyboard = [
        [
            InlineKeyboardButton(text="Confirm ✓", callback_data=f"rem:confirm:{reminder_id}"),
            InlineKeyboardButton(text="Cancel", callback_data=f"rem:cancel:{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reminder_undo_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return [ ↩ Undo ] button timestamped for 60-second expiration."""
    now_ts = int(time.time())
    keyboard = [
        [
            InlineKeyboardButton(text="↩ Undo", callback_data=f"rem:undo:{reminder_id}:{now_ts}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_clarification_keyboard(clarification_id: int, options: List[str]) -> InlineKeyboardMarkup:
    """Return dynamic option buttons for vague deadline disambiguation."""
    keyboard = []
    row = []
    for idx, opt in enumerate(options):
        # Format "Saturday 9:00 AM" into "Saturday · 9 AM" if matching standard pattern
        cleaned_opt = opt.replace(":00", "").replace(" AM", " AM").replace(" PM", " PM")
        if " " in cleaned_opt and " · " not in cleaned_opt:
            parts = cleaned_opt.split(" ", 1)
            btn_text = f"{parts[0]} · {parts[1]}"
        else:
            btn_text = cleaned_opt

        btn = InlineKeyboardButton(text=btn_text, callback_data=f"clrf:pick:{clarification_id}:{idx}")
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
            InlineKeyboardButton(text="🔔 Arm Timers", callback_data=f"deg:arm:{dump_id}"),
            InlineKeyboardButton(text="Cancel", callback_data=f"deg:ignore:{dump_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_focus_keyboard(is_active: bool = False) -> InlineKeyboardMarkup:
    """Return quick buttons for setting or ending Focus Mode."""
    buttons = [
        [
            InlineKeyboardButton(text="25m · Pomodoro", callback_data="focus:set:25"),
            InlineKeyboardButton(text="50m · Deep Work", callback_data="focus:set:50"),
        ],
        [
            InlineKeyboardButton(text="90m · Flow", callback_data="focus:set:90"),
            InlineKeyboardButton(text="2h · Extended", callback_data="focus:set:120"),
        ],
    ]
    if is_active:
        buttons.append([InlineKeyboardButton(text="🛑 Exit Focus Mode", callback_data="focus:off")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_queue_item_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Return action buttons for an individual reminder in the /queue view."""
    keyboard = [
        [
            InlineKeyboardButton(text="✓ Done", callback_data=f"qrem:done:{reminder_id}"),
            InlineKeyboardButton(text="+30m", callback_data=f"qrem:snooze:{reminder_id}"),
            InlineKeyboardButton(text="Cancel", callback_data=f"qrem:cancel:{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
