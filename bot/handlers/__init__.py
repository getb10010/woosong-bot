from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.settings import router as settings_router
from bot.handlers.deadline import router as deadline_router
from bot.handlers.schedule import router as schedule_router
from bot.handlers.admin import router as admin_router
from bot.handlers.help import router as help_router


def setup_routers() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(settings_router)
    router.include_router(deadline_router)
    router.include_router(schedule_router)
    router.include_router(admin_router)
    router.include_router(help_router)
    return router