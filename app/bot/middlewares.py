"""Telegram bot authorization and session middlewares."""

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import settings
from app.bot.messages import format_unauthorized_rejection

logger = logging.getLogger(__name__)


class SingleUserAuthMiddleware(BaseMiddleware):
    """Enforces single-user authorization gate for all updates."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Check configured authorized user ID
        authorized_id = settings.AUTHORIZED_USER_ID

        # If not configured yet (0), allow with setup warning or restrict
        if authorized_id == 0:
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ **ChronoDump is not configured yet.**\n\n"
                    f"Your Telegram User ID is: `{user.id}`\n\n"
                    "Please set `AUTHORIZED_USER_ID` in your `.env` file and restart the bot.",
                    parse_mode="Markdown",
                )
            return

        if user.id != authorized_id:
            logger.warning(f"Unauthorized access attempt from Telegram user ID: {user.id} (@{user.username})")
            if isinstance(event, Message):
                await event.answer(format_unauthorized_rejection(), parse_mode="Markdown")
            elif isinstance(event, CallbackQuery):
                await event.answer("Access restricted.", show_alert=True)
            return

        return await handler(event, data)
