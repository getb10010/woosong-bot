from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.user import User
from bot.utils.i18n import t
from bot.keyboards.onboarding import (
    lang_keyboard, section_keyboard, gender_keyboard,
    yes_no_keyboard, quiet_mode_keyboard, tags_keyboard,
    complete_keyboard,
)
from bot.utils.time_utils import parse_time

router = Router()


class OnboardingState(StatesGroup):
    lang = State()
    section = State()
    gender = State()
    anon_dm = State()
    quiet_mode = State()
    quiet_start = State()
    quiet_end = State()
    tags = State()


# ==================== /start ====================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, user: User | None):
    if user and user.onboarding_complete:
        await message.answer(
            t("help_text", user.lang),
            reply_markup=complete_keyboard(user.lang),
        )
        return

    # Жаңа пайдаланушыны жасау немесе reset
    if not user:
        user = User(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(user)
        await session.flush()

    await state.set_state(OnboardingState.lang)
    await message.answer(
        "🎓 Woosong University KZ\n\n" + t("choose_lang", "kz"),
        reply_markup=lang_keyboard(),
    )


# ==================== Тіл ====================

@router.callback_query(F.data.startswith("lang:"), OnboardingState.lang)
async def on_lang_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    lang = callback.data.split(":")[1]
    await state.update_data(lang=lang)

    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.lang = lang

    await state.set_state(OnboardingState.section)
    await callback.message.edit_text(
        t("choose_section", lang),
        reply_markup=section_keyboard(),
    )
    await callback.answer()


# ==================== Section ====================

@router.callback_query(F.data.startswith("section:"), OnboardingState.section)
async def on_section_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    section = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "kz")

    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.section = section

    await state.update_data(section=section)
    await state.set_state(OnboardingState.gender)
    await callback.message.edit_text(
        t("choose_gender", lang),
        reply_markup=gender_keyboard(lang),
    )
    await callback.answer()


# ==================== Gender ====================

@router.callback_query(F.data.startswith("gender:"), OnboardingState.gender)
async def on_gender_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    gender = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "kz")

    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user and gender != "skip":
        user.gender = gender

    await state.set_state(OnboardingState.anon_dm)
    await callback.message.edit_text(
        t("anon_dm_ask", lang),
        reply_markup=yes_no_keyboard(lang, "anon_dm"),
    )
    await callback.answer()


# ==================== Anon DM ====================

@router.callback_query(F.data.startswith("anon_dm:"), OnboardingState.anon_dm)
async def on_anon_dm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    choice = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "kz")

    result = await session.execute(
        select(User).where(User.tg_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.anon_dm_enabled = choice == "yes"

    await state.set_state(OnboardingState.quiet_mode)
    await callback.message.edit_text(
        t("quiet_mode_ask", lang),
        reply_markup=quiet_mode_keyboard(lang),
    )
    await callback.answer()


# ==================== Quiet Mode ====================

@router.callback_query(F.data == "quiet:default", OnboardingState.quiet_mode)
async def on_quiet_default(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "kz")

    await state.update_data(selected_tags=[])
    await state.set_state(OnboardingState.tags)
    await callback.message.edit_text(
        t("choose_tags", lang),
        reply_markup=tags_keyboard(lang, []),
    )
    await callback.answer()


@router.callback_query(F.data == "quiet:custom", OnboardingState.quiet_mode)
async def on_quiet_custom(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "kz")

    await state.set_state(OnboardingState.quiet_start)
    await callback.message.edit_text(t("quiet_enter_start", lang))
    await callback.answer()


@router.message(OnboardingState.quiet_start)
async def on_quiet_start_input(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "kz")

    parsed = parse_time(message.text)
    if not parsed:
        await message.answer(t("invalid_time_format", lang))
        return

    result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.quiet_start = parsed

    await state.set_state(OnboardingState.quiet_end)
    await message.answer(t("quiet_enter_end", lang))


@router.message(OnboardingState.quiet_end)
async def on_quiet_end_input(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("lang", "kz")

    parsed = parse_time(message.text)
    if not parsed:
        await message.answer(t("invalid_time_format", lang))
        return

    result = await session.execute(
        select(User).where(User.tg_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.quiet_end = parsed

    await state.update_data(selected_tags=[])
    await state.set_state(OnboardingState.tags)
    await message.answer(
        t("choose_tags", lang),
        reply_markup=tags_keyboard(lang, []),
    )


# ==================== Tags ====================

@router.callback_query(F.data.startswith("tag:"), OnboardingState.tags)
async def on_tag_toggle(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    tag = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "kz")
    selected = data.get("selected_tags", [])

    if tag == "done":
        # Тегтерді сақтау
        result = await session.execute(
            select(User).where(User.tg_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.tags = selected
            user.onboarding_complete = True

        await state.clear()
        await callback.message.edit_text(
            t("onboarding_complete", lang),
            reply_markup=complete_keyboard(lang),
        )
        await callback.answer()
        return

    if tag in selected:
        selected.remove(tag)
    else:
        selected.append(tag)

    await state.update_data(selected_tags=selected)
    await callback.message.edit_reply_markup(
        reply_markup=tags_keyboard(lang, selected),
    )
    await callback.answer()


# ==================== /reset ====================

@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext, session: AsyncSession, user: User | None):
    if user:
        user.onboarding_complete = False
        user.section = None
        user.gender = None
        user.tags = []
        lang = user.lang
    else:
        lang = "kz"

    await state.clear()
    await message.answer(t("reset_confirm", lang))