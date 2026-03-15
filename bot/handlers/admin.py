import re
from datetime import datetime, timedelta
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.user import User
from db.models.deadline import Deadline
from db.models.exam import Exam
from db.models.admin_log import AdminLog
from bot.utils.i18n import t
from config import settings

router = Router()


def is_admin(tg_id: int) -> bool:
    return tg_id in settings.admin_ids


# ==================== /admin ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message, user: User | None, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    await message.answer(
        "🛡️ Admin панелі\n\n"
        "Командалар:\n"
        "/broadcast all \"мәтін\"\n"
        "/broadcast section:A1 \"мәтін\"\n"
        "/broadcast tag:sport \"мәтін\"\n"
        "/broadcast urgent \"мәтін\"\n\n"
        "/warn USER_ID \"себеп\"\n"
        "/ban USER_ID 24h \"себеп\"\n"
        "/ban USER_ID 7d \"себеп\"\n"
        "/ban USER_ID perm \"себеп\"\n"
        "/unban USER_ID\n\n"
        "/add_deadline section:A1 \"Атауы\" YYYY-MM-DD\n"
        "/add_exam section:A1 \"Пән\" YYYY-MM-DD room:301\n\n"
        "/stats"
    )


# ==================== /broadcast ====================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    text = message.text.replace("/broadcast", "").strip()

    # Parse target and message
    if text.startswith("all"):
        broadcast_text = text[3:].strip().strip('"')
        query = select(User).where(User.onboarding_complete == True)

    elif text.startswith("section:"):
        match = re.match(r'section:(\S+)\s+"?([^"]+)"?', text)
        if not match:
            await message.answer("Format: /broadcast section:A1 \"message\"")
            return
        section = match.group(1)
        broadcast_text = match.group(2)
        query = select(User).where(
            User.section == section, User.onboarding_complete == True
        )

    elif text.startswith("tag:"):
        match = re.match(r'tag:(\S+)\s+"?([^"]+)"?', text)
        if not match:
            await message.answer("Format: /broadcast tag:sport \"message\"")
            return
        tag = match.group(1)
        broadcast_text = match.group(2)
        query = select(User).where(
            User.tags.any(tag), User.onboarding_complete == True
        )

    elif text.startswith("urgent"):
        broadcast_text = text[6:].strip().strip('"')
        query = select(User).where(User.onboarding_complete == True)

    else:
        await message.answer(
            "Format:\n"
            "/broadcast all \"message\"\n"
            "/broadcast section:A1 \"message\"\n"
            "/broadcast tag:sport \"message\""
        )
        return

    result = await session.execute(query)
    users = result.scalars().all()

    from bot.main import bot as bot_instance

    count = 0
    for u in users:
        try:
            is_urgent = text.startswith("urgent")
            from bot.utils.time_utils import is_quiet_time
            if not is_urgent and u.quiet_start and u.quiet_end:
                if is_quiet_time(u.quiet_start, u.quiet_end):
                    continue

            await bot_instance.send_message(u.tg_id, f"📢 {broadcast_text}")
            count += 1
        except Exception:
            pass

    # Audit log
    admin_result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    admin_user = admin_result.scalar_one_or_none()
    if admin_user:
        log = AdminLog(
            admin_id=admin_user.id,
            action="broadcast",
            details={"text": broadcast_text, "count": count},
        )
        session.add(log)

    await message.answer(t("broadcast_sent", lang, count=count))


# ==================== /warn ====================

@router.message(Command("warn"))
async def cmd_warn(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    match = re.match(r'/warn\s+(\d+)\s+"?([^"]+)"?', message.text)
    if not match:
        await message.answer("Format: /warn USER_TG_ID \"reason\"")
        return

    target_tg_id = int(match.group(1))
    reason = match.group(2)

    result = await session.execute(
        select(User).where(User.tg_id == target_tg_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        await message.answer("❌ User not found.")
        return

    target.warning_count += 1

    from bot.main import bot as bot_instance
    try:
        await bot_instance.send_message(
            target_tg_id,
            f"⚠️ Ескерту!\nСебеп: {reason}\n\nЕскертулер саны: {target.warning_count}"
        )
    except Exception:
        pass

    # Audit
    admin_result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    admin_user = admin_result.scalar_one_or_none()
    if admin_user:
        log = AdminLog(
            admin_id=admin_user.id,
            action="warn_user",
            target_type="user",
            target_id=target.id,
            details={"reason": reason},
        )
        session.add(log)

    await message.answer(t("user_warned", lang))


# ==================== /ban ====================

@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    match = re.match(r'/ban\s+(\d+)\s+(\S+)\s+"?([^"]*)"?', message.text)
    if not match:
        await message.answer("Format: /ban USER_TG_ID 24h|7d|perm \"reason\"")
        return

    target_tg_id = int(match.group(1))
    duration = match.group(2)
    reason = match.group(3)

    result = await session.execute(
        select(User).where(User.tg_id == target_tg_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        await message.answer("❌ User not found.")
        return

    target.is_banned = True
    target.ban_reason = reason

    if duration == "24h":
        target.ban_until = datetime.utcnow() + timedelta(hours=24)
    elif duration == "7d":
        target.ban_until = datetime.utcnow() + timedelta(days=7)
    elif duration == "perm":
        target.ban_until = None  # permanent
    else:
        await message.answer("Duration: 24h | 7d | perm")
        return

    from bot.main import bot as bot_instance
    try:
        await bot_instance.send_message(
            target_tg_id,
            f"🚫 Сіз бандалдыңыз.\nСебеп: {reason}\nМерзімі: {duration}"
        )
    except Exception:
        pass

    # Audit
    admin_result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    admin_user = admin_result.scalar_one_or_none()
    if admin_user:
        log = AdminLog(
            admin_id=admin_user.id,
            action="ban_user",
            target_type="user",
            target_id=target.id,
            details={"duration": duration, "reason": reason},
        )
        session.add(log)

    await message.answer(t("user_banned", lang))


# ==================== /unban ====================

@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    match = re.match(r'/unban\s+(\d+)', message.text)
    if not match:
        await message.answer("Format: /unban USER_TG_ID")
        return

    target_tg_id = int(match.group(1))
    result = await session.execute(
        select(User).where(User.tg_id == target_tg_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        await message.answer("❌ User not found.")
        return

    target.is_banned = False
    target.ban_until = None
    target.ban_reason = None

    await message.answer(t("user_unbanned", lang))


# ==================== /add_deadline ====================

@router.message(Command("add_deadline"))
async def cmd_add_deadline(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    # /add_deadline section:A1 "Математика тапсырма" 2025-03-15
    match = re.match(
        r'/add_deadline\s+section:(\S+)\s+"([^"]+)"\s+(\d{4}-\d{2}-\d{2})',
        message.text
    )
    if not match:
        await message.answer(
            'Format: /add_deadline section:A1 "Title" YYYY-MM-DD'
        )
        return

    section = match.group(1)
    title = match.group(2)
    due_date = datetime.strptime(match.group(3), "%Y-%m-%d")

    admin_result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    admin_user = admin_result.scalar_one_or_none()

    deadline = Deadline(
        title=title,
        due_date=due_date,
        scope="section",
        section=section,
        created_by=admin_user.id if admin_user else None,
    )
    session.add(deadline)

    await message.answer(f"✅ Дедлайн қосылды: {title} ({section}) — {match.group(3)}")


# ==================== /add_exam ====================

@router.message(Command("add_exam"))
async def cmd_add_exam(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    # /add_exam section:A1 "Математика" 2025-06-01 room:301
    match = re.match(
        r'/add_exam\s+section:(\S+)\s+"([^"]+)"\s+(\d{4}-\d{2}-\d{2})(?:\s+room:(\S+))?',
        message.text
    )
    if not match:
        await message.answer(
            'Format: /add_exam section:A1 "Subject" YYYY-MM-DD room:301'
        )
        return

    section = match.group(1)
    subject = match.group(2)
    exam_date = datetime.strptime(match.group(3), "%Y-%m-%d")
    room = match.group(4)

    admin_result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    admin_user = admin_result.scalar_one_or_none()

    exam = Exam(
        section=section,
        subject=subject,
        exam_date=exam_date,
        room=room,
        created_by=admin_user.id if admin_user else None,
    )
    session.add(exam)

    await message.answer(f"✅ Емтихан қосылды: {subject} ({section}) — {match.group(3)}")


# ==================== /stats ====================

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, lang: str):
    if not is_admin(message.from_user.id):
        await message.answer(t("admin_only", lang))
        return

    from sqlalchemy import func
    from db.models.message import Message as MsgModel

    total_users = await session.scalar(
        select(func.count()).select_from(User)
    )
    active_users = await session.scalar(
        select(func.count()).select_from(User).where(User.onboarding_complete == True)
    )
    banned_users = await session.scalar(
        select(func.count()).select_from(User).where(User.is_banned == True)
    )
    total_messages = await session.scalar(
        select(func.count()).select_from(MsgModel)
    )

    sections = await session.execute(
        select(User.section, func.count())
        .where(User.onboarding_complete == True)
        .group_by(User.section)
    )
    section_stats = "\n".join(
        [f"  {row[0]}: {row[1]}" for row in sections.all()]
    )

    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Жалпы: {total_users}\n"
        f"✅ Белсенді: {active_users}\n"
        f"🚫 Банда: {banned_users}\n"
        f"💬 Хабарлама: {total_messages}\n\n"
        f"📚 Section бойынша:\n{section_stats}"
    )