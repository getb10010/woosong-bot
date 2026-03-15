from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
import redis.asyncio as redis
from config import settings


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.redis = redis.from_url(settings.REDIS_URL)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        key = f"throttle:{user_id}"

        current = await self.redis.get(key)
        if current:
            return  # тым жиі жазып жатыр, елемейміз

        await self.redis.setex(key, self.rate_limit, "1")
        return await handler(event, data)