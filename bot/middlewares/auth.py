from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from bot.utils.i18n import t


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]

        tg_user = None
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user

        if tg_user is None:
            return await handler(event, data)

        result = await session.execute(
            select(User).where(User.tg_id == tg_user.id)
        )
        user = result.scalar_one_or_none()

        if user and user.is_banned:
            if user.ban_until and user.ban_until < datetime.utcnow():
                user.is_banned = False
                user.ban_until = None
                user.ban_reason = None
                await session.commit()
            else:
                ban_text = t(
                    "banned",
                    user.lang,
                    reason=user.ban_reason or "—",
                    until=str(user.ban_until) if user.ban_until else "∞",
                )
                if isinstance(event, Message):
                    await event.answer(ban_text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(ban_text, show_alert=True)
                return

        data["user"] = user
        data["lang"] = user.lang if user else "kz"

        return await handler(event, data)