from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from db.models.user import User
from bot.utils.i18n import t
from bot.keyboards.onboarding import complete_keyboard

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None, lang: str):
    await message.answer(
        t("help_text", lang),
        reply_markup=complete_keyboard(lang) if user else None,
    )