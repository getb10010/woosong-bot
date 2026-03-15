from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from api.dependencies import get_db, get_current_user
from api.schemas.message import MessageCreate, MessageResponse
from api.schemas.report import ReportCreate
from api.services.content_filter import check_content
from api.services.rate_limiter import check_rate_limit, check_duplicate_message
from api.services.moderation import process_report
from db.models.message import Message
from db.models.user import User

router = APIRouter()


@router.get("/messages", response_model=list[MessageResponse])
async def get_messages(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.is_hidden == False)
        .order_by(desc(Message.created_at))
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    # view_count жоғарылату
    for msg in messages:
        msg.view_count += 1

    return messages


@router.post("/messages", response_model=MessageResponse)
async def create_message(
    data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit тексеру
    allowed = await check_rate_limit(user.id, "chat_message", 50, 3600)  # 50/сағ
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded")

    # Cooldown тексеру (5 сек)
    cooldown_ok = await check_rate_limit(user.id, "chat_cooldown", 1, 5)
    if not cooldown_ok:
        raise HTTPException(429, "Please wait 5 seconds")

    # Дубликат тексеру
    is_dupe = await check_duplicate_message(user.id, data.content)
    if is_dupe:
        raise HTTPException(400, "Duplicate message detected")

    # Content filter
    filter_result = check_content(data.content)
    if not filter_result["allowed"]:
        raise HTTPException(400, f"Message blocked: {filter_result['reason']}")

    msg = Message(
        user_id=user.id,
        content=data.content,
        reply_to_id=data.reply_to_id,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    return msg


@router.post("/report")
async def report_message(
    data: ReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Report rate limit
    allowed = await check_rate_limit(user.id, "report", 20, 86400)  # 20/күн
    if not allowed:
        raise HTTPException(429, "Too many reports today")

    result = await process_report(
        session=db,
        message_id=data.message_id,
        reporter_id=user.id,
        category=data.category.value,
    )

    if result["status"] == "already_reported":
        raise HTTPException(400, "Already reported")
    if result["status"] == "message_not_found":
        raise HTTPException(404, "Message not found")

    return result