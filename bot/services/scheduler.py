from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session
from db.models.user import User
from db.models.schedule import Schedule
from db.models.deadline import Deadline
from db.models.exam import Exam
from bot.utils.i18n import t
from bot.utils.time_utils import get_today_day_name, is_quiet_time

scheduler = AsyncIOScheduler()
_bot = None


def setup_scheduler(bot):
    global _bot
    _bot = bot

    # Сабақ ескертуі — әр минут сайын тексеру
    scheduler.add_job(
        check_class_reminders,
        IntervalTrigger(minutes=1),
        id="class_reminders",
        replace_existing=True,
    )

    # Дедлайн ескертуі — әр 30 минут
    scheduler.add_job(
        check_deadline_reminders,
        IntervalTrigger(minutes=30),
        id="deadline_reminders",
        replace_existing=True,
    )

    # Емтихан ескертуі — күніне 2 рет (9:00 және 20:00)
    scheduler.add_job(
        check_exam_reminders,
        IntervalTrigger(hours=6),
        id="exam_reminders",
        replace_existing=True,
    )

    scheduler.start()


async def send_to_user(user: User, text: str, force: bool = False):
    """Пайдаланушыға хабарлама жіберу (тыныш режимді тексеріп)"""
    if not force and user.quiet_start and user.quiet_end:
        if is_quiet_time(user.quiet_start, user.quiet_end):
            return False
    try:
        await _bot.send_message(user.tg_id, text)
        return True
    except Exception:
        return False


async def check_class_reminders():
    """Сабаққа 15 минут қалғанда ескерту"""
    now = datetime.now()
    target_time = (now + timedelta(minutes=15)).time()

    async with async_session() as session:
        day = get_today_day_name()

        # Дәл 15 минут қалған сабақтарды табу
        result = await session.execute(
            select(Schedule).where(
                Schedule.day_of_week == day,
                Schedule.start_time.between(
                    target_time.replace(second=0),
                    target_time.replace(second=59),
                ),
            )
        )
        schedules = result.scalars().all()

        for sched in schedules:
            # Осы section студенттерін табу
            users_result = await session.execute(
                select(User).where(
                    User.section == sched.section,
                    User.onboarding_complete == True,
                    User.notify_class == True,
                    User.is_banned == False,
                )
            )
            users = users_result.scalars().all()

            for user in users:
                text = t(
                    "class_reminder", user.lang,
                    minutes=15,
                    subject=sched.subject,
                    start=sched.start_time.strftime("%H:%M"),
                    end=sched.end_time.strftime("%H:%M"),
                    room=sched.room or "—",
                )
                await send_to_user(user, text)


async def check_deadline_reminders():
    """Дедлайн ескертулері: 3 күн, 1 күн, 3 сағат"""
    now = datetime.utcnow()

    async with async_session() as session:
        result = await session.execute(
            select(Deadline).where(Deadline.due_date > now)
        )
        deadlines = result.scalars().all()

        for dl in deadlines:
            diff = dl.due_date - now

            # 3 күн
            if not dl.reminded_3d and diff <= timedelta(days=3):
                dl.reminded_3d = True
                await _send_deadline_notification(session, dl, "deadline_reminder_3d")

            # 1 күн
            if not dl.reminded_1d and diff <= timedelta(days=1):
                dl.reminded_1d = True
                await _send_deadline_notification(session, dl, "deadline_reminder_1d")

            # 3 сағат
            if not dl.reminded_3h and diff <= timedelta(hours=3):
                dl.reminded_3h = True
                await _send_deadline_notification(session, dl, "deadline_reminder_3h")

        await session.commit()


async def _send_deadline_notification(session: AsyncSession, dl: Deadline, msg_key: str):
    """Дедлайн хабарламасын жіберу"""
    if dl.scope == "personal" and dl.user_id:
        result = await session.execute(
            select(User).where(User.id == dl.user_id, User.notify_deadline == True)
        )
        user = result.scalar_one_or_none()
        if user:
            text = t(
                msg_key, user.lang,
                title=dl.title,
                subject=dl.subject or "—",
                due_date=dl.due_date.strftime("%Y-%m-%d %H:%M"),
            )
            await send_to_user(user, text)

    elif dl.scope == "section" and dl.section:
        result = await session.execute(
            select(User).where(
                User.section == dl.section,
                User.onboarding_complete == True,
                User.notify_deadline == True,
                User.is_banned == False,
            )
        )
        users = result.scalars().all()
        for user in users:
            text = t(
                msg_key, user.lang,
                title=dl.title,
                subject=dl.subject or "—",
                due_date=dl.due_date.strftime("%Y-%m-%d %H:%M"),
            )
            await send_to_user(user, text)


async def check_exam_reminders():
    """Емтихан ескертулері: 30, 14, 7, 3, 1 күн"""
    now = datetime.utcnow()

    async with async_session() as session:
        result = await session.execute(
            select(Exam).where(Exam.exam_date > now)
        )
        exams = result.scalars().all()

        for exam in exams:
            diff = exam.exam_date - now
            days = diff.days

            notify_at = None
            if days <= 1 and not exam.notified_1d:
                exam.notified_1d = True
                notify_at = 1
            elif days <= 3 and not exam.notified_3d:
                exam.notified_3d = True
                notify_at = 3
            elif days <= 7 and not exam.notified_7d:
                exam.notified_7d = True
                notify_at = 7
            elif days <= 14 and not exam.notified_14d:
                exam.notified_14d = True
                notify_at = 14
            elif days <= 30 and not exam.notified_30d:
                exam.notified_30d = True
                notify_at = 30

            if notify_at is not None:
                users_result = await session.execute(
                    select(User).where(
                        User.section == exam.section,
                        User.onboarding_complete == True,
                        User.notify_exam == True,
                        User.is_banned == False,
                    )
                )
                users = users_result.scalars().all()

                for user in users:
                    # Студенттің exam_notify_days параметрін тексеру
                    if notify_at > user.exam_notify_days:
                        continue

                    text = t(
                        "exam_reminder", user.lang,
                        days=days,
                        subject=exam.subject,
                        date=exam.exam_date.strftime("%Y-%m-%d"),
                        room=exam.room or "—",
                    )
                    await send_to_user(user, text)

        await session.commit()