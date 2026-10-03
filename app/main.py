"""Main application entrypoint for ChronoDump Telegram Bot."""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import router
from app.bot.middlewares import SingleUserAuthMiddleware
from app.config import settings
from app.scheduler.jobs import scheduler_service
from app.storage.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("chronodump")


async def main() -> None:
    """Initialize resources and launch ChronoDump Telegram Bot."""
    logger.info("Initializing ChronoDump storage...")
    init_db()

    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning(
            "\n"
            "====================================================================\n"
            "⚠️  CHRONODUMP IS NOT CONFIGURED YET\n"
            "Please open your .env file and set:\n"
            "  TELEGRAM_BOT_TOKEN=<your_token_from_botfather>\n"
            "  AUTHORIZED_USER_ID=<your_telegram_id>\n"
            "====================================================================\n"
        )
        print("Please configure .env before starting the bot.")
        return

    logger.info("Initializing Telegram Bot client...")
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # Register single-user authentication middleware
    auth_middleware = SingleUserAuthMiddleware()
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)

    # Register handlers router
    dp.include_router(router)

    # Start persistent scheduler
    logger.info("Starting persistent scheduler service...")
    scheduler_service.start(bot)

    try:
        logger.info("Starting bot polling loop...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Stopping scheduler and closing bot session...")
        scheduler_service.shutdown()
        await bot.session.close()
        logger.info("ChronoDump shutdown cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process interrupted. Exiting.")
