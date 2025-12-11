from __future__ import annotations

from typing import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def agreement_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен", callback_data="agreement:accept")
    return builder.as_markup()


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 Новая съёмка", callback_data="menu:new_session"))
    builder.row(InlineKeyboardButton(text="💬 Генерация по prompt", callback_data="menu:prompt"))
    builder.row(InlineKeyboardButton(text="🕓 История", callback_data="menu:history"))
    builder.row(InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"))
    builder.row(InlineKeyboardButton(text="📄 Политика и соглашение", callback_data="menu:docs"))
    if is_admin:
        builder.row(InlineKeyboardButton(text="🛠 Админка", callback_data="menu:admin"))
    return builder.as_markup()


def styles_keyboard(styles: Iterable[str | tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for style in styles:
        if isinstance(style, tuple):
            value, label = style
        else:
            value, label = style, style.capitalize()
        builder.button(text=label, callback_data=f"style:{value}")
    builder.button(text="🏠 Домой", callback_data="menu:home")
    return builder.adjust(2).as_markup()


def orientation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Вертикаль (9:16)", callback_data="orientation:vertical")
    builder.button(text="Горизонталь (16:9)", callback_data="orientation:horizontal")
    builder.button(text="🔙 Назад", callback_data="menu:new_session")
    return builder.adjust(1).as_markup()


def faces_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Загрузить лицо", callback_data="faces:upload")
    builder.button(text="🧑‍🦰 Выбрать сохранённое", callback_data="faces:list")
    builder.button(text="🗑 Удалить лицо", callback_data="faces:delete_list")
    builder.button(text="⬅️ Назад", callback_data="menu:home")
    builder.button(text="✅ Готово", callback_data="faces:done")
    return builder.adjust(1).as_markup()


def prompt_templates_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    templates = [
        ("🎨 Art", "template:art"),
        ("🌀 Сюрреализм", "template:surreal"),
        ("💎 CGI", "template:cg"),
        ("🌃 Неон", "template:neon"),
    ]
    for text, data in templates:
        builder.button(text=text, callback_data=data)
    builder.button(text="✍️ Свой prompt", callback_data="template:custom")
    builder.button(text="🏠 Домой", callback_data="menu:home")
    return builder.adjust(2).as_markup()


def sessions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Новая съёмка", callback_data="menu:new_session")
    builder.button(text="🔗 Поделиться", callback_data="session:share")
    builder.button(text="🏠 Домой", callback_data="menu:home")
    return builder.adjust(1).as_markup()


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📈 Статистика", callback_data="admin:stats"))
    builder.row(InlineKeyboardButton(text="💳 Выдать токены", callback_data="admin:give_tokens"))
    builder.row(InlineKeyboardButton(text="🧑‍💻 Управление админами", callback_data="admin:manage_admins"))
    builder.row(InlineKeyboardButton(text="🎞 Примеры", callback_data="admin:examples"))
    builder.row(InlineKeyboardButton(text="🚫 Баны", callback_data="admin:bans"))
    builder.row(InlineKeyboardButton(text="🏠 Домой", callback_data="menu:home"))
    return builder.adjust(1).as_markup()


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="admin:cancel")
    return builder.as_markup()


def admin_manage_user_keyboard(user_id: int, is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.button(text="Забрать доступ", callback_data=f"admin_manage:revoke:{user_id}")
    else:
        builder.button(text="Дать админку", callback_data=f"admin_manage:grant:{user_id}")
    builder.button(text="Отмена", callback_data="admin:cancel")
    return builder.as_markup()
