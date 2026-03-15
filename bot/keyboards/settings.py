from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.i18n import t


def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("settings_lang", lang), callback_data="set:lang"
        )],
        [InlineKeyboardButton(
            text=t("settings_section", lang), callback_data="set:section"
        )],
        [InlineKeyboardButton(
            text=t("settings_quiet", lang), callback_data="set:quiet"
        )],
        [InlineKeyboardButton(
            text=t("settings_anon_dm", lang), callback_data="set:anon_dm"
        )],
        [InlineKeyboardButton(
            text=t("settings_notifications", lang), callback_data="set:notifications"
        )],
        [InlineKeyboardButton(
            text=t("settings_tags", lang), callback_data="set:tags"
        )],
    ])


def notification_keyboard(lang: str, user) -> InlineKeyboardMarkup:
    def status(val: bool) -> str:
        return "✅" if val else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{status(user.notify_class)} Сабақ",
            callback_data="notif:class"
        )],
        [InlineKeyboardButton(
            text=f"{status(user.notify_break)} Үзіліс",
            callback_data="notif:break"
        )],
        [InlineKeyboardButton(
            text=f"{status(user.notify_deadline)} Дедлайн",
            callback_data="notif:deadline"
        )],
        [InlineKeyboardButton(
            text=f"{status(user.notify_exam)} Емтихан",
            callback_data="notif:exam"
        )],
    ])