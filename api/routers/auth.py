from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_current_user
from db.models.user import User

router = APIRouter()


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "section": user.section,
        "lang": user.lang,
        "anon_dm_enabled": user.anon_dm_enabled,
        "is_admin": user.is_admin or user.tg_id in __import__("config").settings.admin_ids,
        "created_at": user.created_at.isoformat(),
    }