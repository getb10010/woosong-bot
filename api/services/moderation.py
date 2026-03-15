from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.message import Message
from db.models.report import Report
from db.models.user import User


async def process_report(
    session: AsyncSession,
    message_id: int,
    reporter_id: int,
    category: str,
) -> dict:
    """Report өңдеу + авто-жасыру тексеру"""

    # Бұрын report берген бе?
    existing = await session.execute(
        select(Report).where(
            Report.message_id == message_id,
            Report.reporter_id == reporter_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_reported"}

    # Reporter credibility алу
    reporter = await session.execute(
        select(User).where(User.id == reporter_id)
    )
    reporter_user = reporter.scalar_one_or_none()
    credibility = reporter_user.report_credibility if reporter_user else 1.0

    # Report қосу
    report = Report(
        message_id=message_id,
        reporter_id=reporter_id,
        category=category,
    )
    session.add(report)

    # Хабарламаның report_count жаңарту
    msg_result = await session.execute(
        select(Message).where(Message.id == message_id)
    )
    message = msg_result.scalar_one_or_none()
    if not message:
        return {"status": "message_not_found"}

    message.report_count += 1

    # Авто-жасыру тексеру: 5+ report ЖӘНЕ 30%+ view
    should_hide = False
    if message.report_count >= 5:
        if message.view_count > 0:
            ratio = message.report_count / message.view_count
            if ratio >= 0.30:
                should_hide = True
        else:
            should_hide = True  # view_count 0 болса 5 report жеткілікті

    if should_hide and not message.is_hidden:
        message.is_hidden = True
        message.hidden_reason = "auto_report"

        # Жіберушінің auto_hide_count жоғарылату
        author = await session.execute(
            select(User).where(User.id == message.user_id)
        )
        author_user = author.scalar_one_or_none()
        if author_user:
            author_user.auto_hide_count += 1

            # 3 рет жасырылса → автоматты 24 сағат бан
            if author_user.auto_hide_count >= 3 and not author_user.is_banned:
                from datetime import datetime, timedelta
                author_user.is_banned = True
                author_user.ban_until = datetime.utcnow() + timedelta(hours=24)
                author_user.ban_reason = "auto_ban: 3+ messages hidden by reports"

        return {"status": "hidden", "auto_ban": author_user.auto_hide_count >= 3 if author_user else False}

    return {"status": "reported", "report_count": message.report_count}