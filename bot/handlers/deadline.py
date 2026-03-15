import re
from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from db.models.deadline import Deadline
from bot.utils.i18n import t

router = Router()


@router.message(Command("deadline"))
async def cmd_deadline(message: Message, user: User | None, lang: str, session: AsyncSession):
    if not user or not user.onboarding_complete:
        await message.answer(t("not_registered", lang))
        return

    text = message.text.replace("/deadline", "").strip()

    # Формат: /deadline "Тапсырма атауы" 2025-03-15
    match = re.match(r'"([^"]+)"\s+(\d{4}-\d{2}-\d{2})', text)
    if not match:
        await message.answer(t("deadline_format", lang))
        return

    title = match.group(1)
    try:
        due_date = datetime.strptime(match.group(2), "%Y-%m-%d")
    except ValueError:
        await message.answer(t("deadline_format", lang))
        return

    if due_date < datetime.utcnow():
        await message.answer("❌ Дедлайн мерзімі өткен күн болмауы керек.")
        return

    deadline = Deadline(
        title=title,
        due_date=due_date,
        scope="personal",
        user_id=user.id,
        created_by=user.id,
    )
    session.add(deadline)

    await message.answer(
        t("deadline_added", lang, title=title, due_date=match.group(2))
    )