from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_

from api.dependencies import get_db, get_current_user
from api.schemas.dm import DMThreadCreate, DMMessageCreate, DMThreadResponse, DMMessageResponse
from api.services.rate_limiter import check_rate_limit
from api.services.content_filter import check_content
from db.models.anon_dm import AnonDMThread, AnonDMMessage
from db.models.user import User

router = APIRouter()


@router.get("/threads", response_model=list[DMThreadResponse])
async def get_threads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnonDMThread).where(
            or_(
                AnonDMThread.sender_id == user.id,
                AnonDMThread.receiver_id == user.id,
            ),
            AnonDMThread.sender_blocked == False,
        ).order_by(desc(AnonDMThread.created_at))
    )
    return result.scalars().all()


@router.post("/threads", response_model=DMThreadResponse)
async def create_thread(
    data: DMThreadCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit: 3 жаңа thread / күн
    allowed = await check_rate_limit(user.id, "dm_new_thread", 3, 86400)
    if not allowed:
        raise HTTPException(429, "Max 3 new conversations per day")

    # Receiver тексеру
    receiver = await db.execute(
        select(User).where(User.id == data.receiver_id)
    )
    recv = receiver.scalar_one_or_none()
    if not recv:
        raise HTTPException(404, "User not found")
    if not recv.anon_dm_enabled:
        raise HTTPException(403, "User has disabled anonymous DMs")
    if recv.id == user.id:
        raise HTTPException(400, "Cannot send DM to yourself")

    # Бұрын thread бар ма?
    existing = await db.execute(
        select(AnonDMThread).where(
            AnonDMThread.sender_id == user.id,
            AnonDMThread.receiver_id == recv.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Thread already exists")

    thread = AnonDMThread(
        sender_id=user.id,
        receiver_id=recv.id,
        status="pending",
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)
    return thread


@router.post("/threads/{thread_id}/accept")
async def accept_thread(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnonDMThread).where(AnonDMThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread.receiver_id != user.id:
        raise HTTPException(403, "Not your thread")

    thread.status = "accepted"
    return {"status": "accepted"}


@router.post("/threads/{thread_id}/reject")
async def reject_thread(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnonDMThread).where(AnonDMThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread.receiver_id != user.id:
        raise HTTPException(403, "Not your thread")

    thread.status = "rejected"
    return {"status": "rejected"}


@router.post("/threads/{thread_id}/block")
async def block_sender(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnonDMThread).where(AnonDMThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread.receiver_id != user.id:
        raise HTTPException(403, "Not your thread")

    thread.sender_blocked = True
    return {"status": "blocked"}


@router.get("/threads/{thread_id}/messages", response_model=list[DMMessageResponse])
async def get_dm_messages(
    thread_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Thread тексеру
    thread = await db.execute(
        select(AnonDMThread).where(AnonDMThread.id == thread_id)
    )
    t = thread.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Thread not found")
    if t.sender_id != user.id and t.receiver_id != user.id:
        raise HTTPException(403, "Access denied")
    if t.status != "accepted":
        raise HTTPException(403, "Thread not accepted")

    result = await db.execute(
        select(AnonDMMessage)
        .where(AnonDMMessage.thread_id == thread_id)
        .order_by(AnonDMMessage.created_at)
    )
    messages = result.scalars().all()

    response = []
    for msg in messages:
        # Оқылды деп белгілеу
        if msg.sender_id != user.id and not msg.is_read:
            msg.is_read = True

        response.append(DMMessageResponse(
            id=msg.id,
            content=msg.content,
            is_mine=msg.sender_id == user.id,
            is_read=msg.is_read,
            created_at=msg.created_at,
        ))
    return response


@router.post("/threads/{thread_id}/messages", response_model=DMMessageResponse)
async def send_dm_message(
    thread_id: int,
    data: DMMessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Thread тексеру
    thread = await db.execute(
        select(AnonDMThread).where(AnonDMThread.id == thread_id)
    )
    t = thread.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Thread not found")
    if t.sender_id != user.id and t.receiver_id != user.id:
        raise HTTPException(403, "Access denied")
    if t.status != "accepted":
        raise HTTPException(403, "Thread not accepted yet")
    if t.sender_blocked:
        raise HTTPException(403, "You have been blocked")

    # Rate limit: 20 хабарлама / thread / күн
    allowed = await check_rate_limit(
        user.id, f"dm_thread_{thread_id}", 20, 86400
    )
    if not allowed:
        raise HTTPException(429, "Max 20 messages per thread per day")

    # Content filter
    filter_result = check_content(data.content)
    if not filter_result["allowed"]:
        raise HTTPException(400, f"Message blocked: {filter_result['reason']}")

    msg = AnonDMMessage(
        thread_id=thread_id,
        sender_id=user.id,
        content=data.content,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    return DMMessageResponse(
        id=msg.id,
        content=msg.content,
        is_mine=True,
        is_read=False,
        created_at=msg.created_at,
    )