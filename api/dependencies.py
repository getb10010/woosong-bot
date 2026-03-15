import hashlib
import hmac
from urllib.parse import unquote, parse_qs
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import async_session
from db.models.user import User
from config import settings


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def validate_init_data(init_data: str) -> dict:
    """Telegram Mini App initData тексеру"""
    parsed = parse_qs(init_data)
    check_hash = parsed.get("hash", [None])[0]
    if not check_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    data_check_arr = []
    for key, values in sorted(parsed.items()):
        if key != "hash":
            data_check_arr.append(f"{key}={values[0]}")

    data_check_string = "\n".join(data_check_arr)

    secret_key = hmac.new(
        b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if calculated_hash != check_hash:
        raise HTTPException(status_code=401, detail="Invalid hash")

    return parsed


async def get_current_user(
    x_init_data: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Mini App пайдаланушысын тексеру"""
    data = validate_init_data(unquote(x_init_data))

    import json
    user_data = json.loads(data.get("user", ["{}"])[0])
    tg_id = user_data.get("id")

    if not tg_id:
        raise HTTPException(status_code=401, detail="Invalid user data")

    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin and user.tg_id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Admin only")
    return user