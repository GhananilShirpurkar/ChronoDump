"""Execution callbacks for scheduled reminders and vague-time clarification pings."""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.bot.keyboards import get_clarification_keyboard, get_reminder_action_keyboard
from app.bot.messages import format_clarification_prompt, format_reminder_alert
from app.storage.database import (
    get_reminder,
    get_vague_clarification,
    mark_reminder_fired,
)

logger = logging.getLogger(__name__)

# Global bot reference for scheduler callbacks
_BOT_INSTANCE: Optional[Bot] = None


def set_bot_instance(bot: Bot) -> None:
    """Register the active aiogram Bot instance for scheduled notifications."""
    global _BOT_INSTANCE
    _BOT_INSTANCE = bot
    logger.info("Bot instance registered with scheduler reminders module.")


def get_bot_instance() -> Optional[Bot]:
    """Retrieve active bot instance."""
    return _BOT_INSTANCE


async def execute_reminder_job(reminder_id: int) -> None:
    """
    Top-level importable callback fired by APScheduler when a reminder target timestamp is reached.
    Survives restarts and pickle serialization.
    """
    logger.info(f"Fired scheduled reminder job for reminder_id={reminder_id}")
    reminder = get_reminder(reminder_id)
    if not reminder:
        logger.warning(f"Reminder with ID {reminder_id} not found in database.")
        return

    # Check status; do not alert if already completed or cancelled
    if reminder.status not in ("pending", "snoozed"):
        logger.info(f"Skipping reminder {reminder_id} with status '{reminder.status}'")
        return

    # Check if user is currently in Focus Mode
    from datetime import timedelta
    from app.storage.database import get_user_focus, snooze_reminder
    from app.scheduler.jobs import scheduler_service
    focus_until = get_user_focus(reminder.user_id)
    if focus_until:
        logger.info(f"User {reminder.user_id} in Focus Mode until {focus_until}. Postponing reminder {reminder_id}.")
        new_target = focus_until + timedelta(seconds=1)
        new_job_id = scheduler_service.reschedule_reminder(reminder_id, new_target)
        snooze_reminder(reminder_id, new_target, f"Delayed by Focus Mode until {focus_until.strftime('%I:%M %p')}", new_job_id)
        return

    bot = get_bot_instance()
    if not bot:
        logger.error(f"Cannot deliver reminder {reminder_id}: Bot instance not initialized!")
        return

    text = format_reminder_alert(reminder.task)
    reply_markup = get_reminder_action_keyboard(reminder.id)

    try:
        await bot.send_message(
            chat_id=reminder.user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        mark_reminder_fired(reminder.id)
        logger.info(f"Delivered reminder alert {reminder_id} to user {reminder.user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send reminder alert {reminder_id} via Telegram: {e}")


async def execute_vague_clarification_job(clarification_id: int) -> None:
    """
    Top-level importable callback fired by APScheduler to prompt user for ambiguous deadline clarification.
    """
    logger.info(f"Fired vague clarification job for clarification_id={clarification_id}")
    clarification = get_vague_clarification(clarification_id)
    if not clarification:
        logger.warning(f"Clarification {clarification_id} not found in database.")
        return

    if clarification.status != "pending":
        logger.info(f"Clarification {clarification_id} already resolved ({clarification.status}).")
        return

    bot = get_bot_instance()
    if not bot:
        logger.error(f"Cannot deliver clarification {clarification_id}: Bot instance not initialized!")
        return

    text = format_clarification_prompt(clarification.task, clarification.window)
    reply_markup = get_clarification_keyboard(clarification.id, clarification.options)

    try:
        await bot.send_message(
            chat_id=clarification.user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        logger.info(f"Delivered clarification prompt {clarification_id} to user {clarification.user_id}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send clarification prompt {clarification_id} via Telegram: {e}")
