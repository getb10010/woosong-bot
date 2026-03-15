from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from api.dependencies import get_db, get_current_user
from api.schemas.lost_found import LostFoundCreate, LostFoundResponse
from api.services.rate_limiter import check_rate_limit
from db.models.lost_found import LostFound
from db.models.user import User

router = APIRouter()


@router.get("/items", response_model=list[LostFoundResponse])
async def get_items(
    type: str = Query(None),
    resolved: bool = Query(False),
    limit: int = Query(20, le=50),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(LostFound).where(LostFound.is_resolved == resolved)
    if type:
        query = query.where(LostFound.type == type)
    query = query.order_by(desc(LostFound.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/items", response_model=LostFoundResponse)
async def create_item(
    data: LostFoundCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(user.id, "lost_found", 3, 86400)
    if not allowed:
        raise HTTPException(429, "Max 3 posts per day")

    item = LostFound(
        user_id=user.id,
        type=data.type.value,
        description=data.description,
        location=data.location,
        photo_url=data.photo_url,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.post("/items/{item_id}/resolve")
async def resolve_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LostFound).where(LostFound.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    if item.user_id != user.id:
        raise HTTPException(403, "Only author can resolve")
    item.is_resolved = True
    item.resolved_at = datetime.utcnow()
    return {"status": "resolved"}