from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.user import User
from db.models.schedule import Schedule
from bot.utils.i18n import t
from bot.utils.time_utils import get_today_day_name

router = Router()


@router.message(Command("schedule"))
async def cmd_schedule(message: Message, user: User | None, lang: str, session: AsyncSession):
    if not user or not user.onboarding_complete:
        await message.answer(t("not_registered", lang))
        return

    day = get_today_day_name()
    result = await session.execute(
        select(Schedule)
        .where(Schedule.section == user.section, Schedule.day_of_week == day)
        .order_by(Schedule.start_time)
    )
    schedules = result.scalars().all()

    if not schedules:
        await message.answer(t("schedule_empty", lang))
        return

    lines = []
    for s in schedules:
        line = (
            f"📖 {s.subject}\n"
            f"   🕐 {s.start_time.strftime('%H:%M')} — {s.end_time.strftime('%H:%M')}"
        )
        if s.room:
            line += f"\n   🏫 Каб. {s.room}"
        if s.teacher:
            line += f"\n   👨‍🏫 {s.teacher}"
        lines.append(line)

    schedule_text = "\n\n".join(lines)
    await message.answer(
        t("schedule_today", lang, section=user.section, schedule=schedule_text)
    )