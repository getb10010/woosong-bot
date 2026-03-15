from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from api.dependencies import get_db, get_current_user
from api.schemas.qa import (
    QAPostCreate, QAPostResponse,
    QAAnswerCreate, QAAnswerResponse,
    VoteCreate,
)
from api.services.rate_limiter import check_rate_limit
from api.services.content_filter import check_content
from db.models.qa import QAPost, QAAnswer, QAVote
from db.models.user import User

router = APIRouter()


@router.get("/posts", response_model=list[QAPostResponse])
async def get_posts(
    tag: str = Query(None),
    resolved: bool = Query(None),
    sort: str = Query("new"),  # new | unanswered | popular
    limit: int = Query(20, le=50),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(QAPost).where(QAPost.is_hidden == False)

    if tag:
        query = query.where(QAPost.subject_tag == tag)
    if resolved is not None:
        query = query.where(QAPost.is_resolved == resolved)

    if sort == "unanswered":
        # Жауапсыз сұрақтар
        subq = select(func.count(QAAnswer.id)).where(
            QAAnswer.post_id == QAPost.id
        ).correlate(QAPost).scalar_subquery()
        query = query.where(subq == 0)

    query = query.order_by(desc(QAPost.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    response = []
    for post in posts:
        post.view_count += 1
        # Жауап санын есептеу
        ans_count = await db.scalar(
            select(func.count(QAAnswer.id)).where(QAAnswer.post_id == post.id)
        )
        # Username алу
        username = None
        if not post.is_anonymous:
            user_result = await db.execute(
                select(User.username).where(User.id == post.user_id)
            )
            username = user_result.scalar_one_or_none()

        response.append(QAPostResponse(
            id=post.id,
            question=post.question,
            subject_tag=post.subject_tag,
            is_anonymous=post.is_anonymous,
            is_resolved=post.is_resolved,
            username=username,
            created_at=post.created_at,
            answer_count=ans_count or 0,
        ))

    return response


@router.post("/posts", response_model=QAPostResponse)
async def create_post(
    data: QAPostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(user.id, "qa_post", 5, 86400)
    if not allowed:
        raise HTTPException(429, "Max 5 questions per day")

    filter_result = check_content(data.question)
    if not filter_result["allowed"]:
        raise HTTPException(400, f"Content blocked: {filter_result['reason']}")

    post = QAPost(
        user_id=user.id,
        question=data.question,
        subject_tag=data.subject_tag,
        is_anonymous=data.is_anonymous,
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)

    return QAPostResponse(
        id=post.id,
        question=post.question,
        subject_tag=post.subject_tag,
        is_anonymous=post.is_anonymous,
        is_resolved=False,
        username=None if post.is_anonymous else user.username,
        created_at=post.created_at,
        answer_count=0,
    )


@router.get("/posts/{post_id}/answers", response_model=list[QAAnswerResponse])
async def get_answers(
    post_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QAAnswer)
        .where(QAAnswer.post_id == post_id, QAAnswer.is_hidden == False)
        .order_by(desc(QAAnswer.upvotes - QAAnswer.downvotes))
    )
    answers = result.scalars().all()

    response = []
    for ans in answers:
        username = None
        if not ans.is_anonymous:
            u = await db.execute(
                select(User.username).where(User.id == ans.user_id)
            )
            username = u.scalar_one_or_none()

        response.append(QAAnswerResponse(
            id=ans.id,
            content=ans.content,
            is_anonymous=ans.is_anonymous,
            upvotes=ans.upvotes,
            downvotes=ans.downvotes,
            username=username,
            created_at=ans.created_at,
        ))
    return response


@router.post("/posts/{post_id}/answers", response_model=QAAnswerResponse)
async def create_answer(
    post_id: int,
    data: QAAnswerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(user.id, "qa_answer", 30, 86400)
    if not allowed:
        raise HTTPException(429, "Max 30 answers per day")

    filter_result = check_content(data.content)
    if not filter_result["allowed"]:
        raise HTTPException(400, f"Content blocked: {filter_result['reason']}")

    # Post бар ма тексеру
    post = await db.execute(select(QAPost).where(QAPost.id == post_id))
    if not post.scalar_one_or_none():
        raise HTTPException(404, "Post not found")

    answer = QAAnswer(
        post_id=post_id,
        user_id=user.id,
        content=data.content,
        is_anonymous=data.is_anonymous,
    )
    db.add(answer)
    await db.flush()
    await db.refresh(answer)

    return QAAnswerResponse(
        id=answer.id,
        content=answer.content,
        is_anonymous=answer.is_anonymous,
        upvotes=0,
        downvotes=0,
        username=None if answer.is_anonymous else user.username,
        created_at=answer.created_at,
    )


@router.post("/answers/{answer_id}/vote")
async def vote_answer(
    answer_id: int,
    data: VoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(user.id, "qa_vote", 50, 86400)
    if not allowed:
        raise HTTPException(429, "Max 50 votes per day")

    # Бұрын дауыс берген бе?
    existing = await db.execute(
        select(QAVote).where(
            QAVote.answer_id == answer_id, QAVote.user_id == user.id
        )
    )
    vote_record = existing.scalar_one_or_none()

    answer = await db.execute(
        select(QAAnswer).where(QAAnswer.id == answer_id)
    )
    ans = answer.scalar_one_or_none()
    if not ans:
        raise HTTPException(404, "Answer not found")

    if vote_record:
        # Дауысты өзгерту
        old_vote = vote_record.vote
        vote_record.vote = data.vote
        if old_vote == 1:
            ans.upvotes -= 1
        else:
            ans.downvotes -= 1
    else:
        vote_record = QAVote(
            answer_id=answer_id, user_id=user.id, vote=data.vote
        )
        db.add(vote_record)

    if data.vote == 1:
        ans.upvotes += 1
    else:
        ans.downvotes += 1

    return {"status": "voted", "upvotes": ans.upvotes, "downvotes": ans.downvotes}


@router.post("/posts/{post_id}/resolve")
async def resolve_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(QAPost).where(QAPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.user_id != user.id:
        raise HTTPException(403, "Only author can resolve")

    post.is_resolved = True
    return {"status": "resolved"}