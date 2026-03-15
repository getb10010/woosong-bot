import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from db.database import init_db
from bot.handlers import setup_routers
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.services.scheduler import setup_scheduler
from bot.utils.i18n import load_locales

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


async def main():
    logger.info("Starting Woosong Bot...")

    # i18n жүктеу
    load_locales()

    # Database
    await init_db()
    logger.info("Database initialized")

    # Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(ThrottleMiddleware(rate_limit=1))

    # Handlers
    router = setup_routers()
    dp.include_router(router)

    # Scheduler
    setup_scheduler(bot)
    logger.info("Scheduler started")

    # Start polling
    logger.info("Bot is running!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())