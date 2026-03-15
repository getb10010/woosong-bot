from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.user import User
from bot.utils.i18n import t
from bot.keyboards.settings import settings_keyboard, notification_keyboard
from bot.keyboards.onboarding import (
    lang_keyboard, section_keyboard, quiet_mode_keyboard,
    yes_no_keyboard, tags_keyboard,
)

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message, user: User | None, lang: str):
    if not user or not user.onboarding_complete:
        await message.answer(t("not_registered", lang))
        return
    await message.answer(
        t("settings_menu", lang),
        reply_markup=settings_keyboard(lang),
    )


# Тіл өзгерту
@router.callback_query(F.data == "set:lang")
async def set_lang(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌐", reply_markup=lang_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def change_lang(callback: CallbackQuery, session: AsyncSession):
    lang = callback.data.split(":")[1]
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.lang = lang
    await callback.message.edit_text(t("saved", lang))
    await callback.answer()


# Section өзгерту
@router.callback_query(F.data == "set:section")
async def set_section(callback: CallbackQuery, lang: str):
    await callback.message.edit_text(
        t("choose_section", lang),
        reply_markup=section_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("section:"))
async def change_section(callback: CallbackQuery, session: AsyncSession, lang: str):
    section = callback.data.split(":")[1]
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.section = section
    await callback.message.edit_text(t("saved", lang))
    await callback.answer()


# Anon DM
@router.callback_query(F.data == "set:anon_dm")
async def set_anon_dm(callback: CallbackQuery, lang: str):
    await callback.message.edit_text(
        t("anon_dm_ask", lang),
        reply_markup=yes_no_keyboard(lang, "set_dm"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_dm:"))
async def change_anon_dm(callback: CallbackQuery, session: AsyncSession, lang: str):
    choice = callback.data.split(":")[1]
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.anon_dm_enabled = choice == "yes"
    await callback.message.edit_text(t("saved", lang))
    await callback.answer()


# Notification preferences
@router.message(Command("notifications"))
async def cmd_notifications(message: Message, user: User | None, lang: str):
    if not user or not user.onboarding_complete:
        await message.answer(t("not_registered", lang))
        return
    await message.answer(
        t(
            "notification_settings", lang,
            class_status=t("on" if user.notify_class else "off", lang),
            break_status=t("on" if user.notify_break else "off", lang),
            deadline_status=t("on" if user.notify_deadline else "off", lang),
            exam_status=t("on" if user.notify_exam else "off", lang),
        ),
        reply_markup=notification_keyboard(lang, user),
    )


@router.callback_query(F.data == "set:notifications")
async def set_notifications_cb(callback: CallbackQuery, session: AsyncSession, lang: str):
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return
    await callback.message.edit_text(
        t(
            "notification_settings", lang,
            class_status=t("on" if user.notify_class else "off", lang),
            break_status=t("on" if user.notify_break else "off", lang),
            deadline_status=t("on" if user.notify_deadline else "off", lang),
            exam_status=t("on" if user.notify_exam else "off", lang),
        ),
        reply_markup=notification_keyboard(lang, user),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("notif:"))
async def toggle_notification(callback: CallbackQuery, session: AsyncSession, lang: str):
    field = callback.data.split(":")[1]
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    field_map = {
        "class": "notify_class",
        "break": "notify_break",
        "deadline": "notify_deadline",
        "exam": "notify_exam",
    }
    attr = field_map.get(field)
    if attr:
        setattr(user, attr, not getattr(user, attr))

    await callback.message.edit_text(
        t(
            "notification_settings", lang,
            class_status=t("on" if user.notify_class else "off", lang),
            break_status=t("on" if user.notify_break else "off", lang),
            deadline_status=t("on" if user.notify_deadline else "off", lang),
            exam_status=t("on" if user.notify_exam else "off", lang),
        ),
        reply_markup=notification_keyboard(lang, user),
    )
    await callback.answer()


# Quiet mode
@router.callback_query(F.data == "set:quiet")
async def set_quiet(callback: CallbackQuery, lang: str):
    await callback.message.edit_text(
        t("quiet_mode_ask", lang),
        reply_markup=quiet_mode_keyboard(lang),
    )
    await callback.answer()


# Tags
@router.callback_query(F.data == "set:tags")
async def set_tags(callback: CallbackQuery, session: AsyncSession, lang: str):
    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    current_tags = user.tags if user and user.tags else []
    await callback.message.edit_text(
        t("choose_tags", lang),
        reply_markup=tags_keyboard(lang, current_tags),
    )
    await callback.answer()