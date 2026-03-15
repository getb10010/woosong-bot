from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.utils.i18n import t
from config import settings


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ]
    ])


SECTIONS = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]


def section_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, sec in enumerate(SECTIONS):
        row.append(InlineKeyboardButton(text=sec, callback_data=f"section:{sec}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gender_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("gender_male", lang), callback_data="gender:male")],
        [InlineKeyboardButton(text=t("gender_female", lang), callback_data="gender:female")],
        [InlineKeyboardButton(text=t("gender_skip", lang), callback_data="gender:skip")],
    ])


def yes_no_keyboard(lang: str, prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("yes", lang), callback_data=f"{prefix}:yes"),
            InlineKeyboardButton(text=t("no", lang), callback_data=f"{prefix}:no"),
        ]
    ])


def quiet_mode_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("quiet_keep_default", lang), callback_data="quiet:default"
        )],
        [InlineKeyboardButton(
            text=t("quiet_custom", lang), callback_data="quiet:custom"
        )],
    ])


TAGS = ["sport", "events", "scholarship", "dormitory", "clubs"]


def tags_keyboard(lang: str, selected: list = None) -> InlineKeyboardMarkup:
    if selected is None:
        selected = []
    buttons = []
    for tag in TAGS:
        check = "✅ " if tag in selected else ""
        label = t(f"tag_{tag}", lang)
        buttons.append([InlineKeyboardButton(
            text=f"{check}{label}", callback_data=f"tag:{tag}"
        )])
    buttons.append([InlineKeyboardButton(
        text=t("tags_done", lang), callback_data="tag:done"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def complete_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    if settings.MINI_APP_URL:
        buttons.append([InlineKeyboardButton(
            text=t("open_mini_app", lang),
            web_app=WebAppInfo(url=settings.MINI_APP_URL),
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)