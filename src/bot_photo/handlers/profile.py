from __future__ import annotations

from aiogram import Router, types

from ..utils import get_faces_repo, get_settings, get_users_repo

router = Router(name="profile")


@router.callback_query(lambda c: c.data == "menu:profile")
async def open_profile(callback: types.CallbackQuery) -> None:
    users_repo = get_users_repo(callback.message.bot)
    faces_repo = get_faces_repo(callback.message.bot)
    user = await users_repo.get_by_id(callback.from_user.id)
    if not user:
        settings = get_settings(callback.message.bot)
        user = await users_repo.upsert_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            is_admin=callback.from_user.id in settings.admin_ids,
            starting_tokens=settings.starting_tokens,
            hourly_limit=settings.hourly_limit,
        )
    faces = await faces_repo.list_faces(callback.from_user.id)
    tokens = user.tokens if user else 0
    registered = user.last_seen_at.strftime("%d.%m.%Y") if user and user.last_seen_at else "-"
    text = (
        "👤 Твой профиль\n\n"
        f"🆔 ID: {callback.from_user.id}\n"
        f"🙋 Имя: {callback.from_user.full_name or callback.from_user.username or '-'}\n"
        f"💎 Баланс: {tokens} токенов\n"
        f"📅 Зарегистрирован: {registered}\n"
        f"🖼️ Лиц сохранено: {len(faces)} / 10\n"
        "ℹ️ Тариф: 5 токенов = 1 фото."
    )
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="profile:topup")],
            [types.InlineKeyboardButton(text="🖼️ Мои лица", callback_data="profile:faces")],
            [types.InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home")],
        ]
    )
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "profile:topup")
async def profile_topup(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>Пополнить баланс</b>\n\nВыберите удобный способ оплаты:",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="СБП (ручное зачисление)", callback_data="payment:sbp")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile")],
            ]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "profile:faces")
async def profile_faces(callback: types.CallbackQuery) -> None:
    faces_repo = get_faces_repo(callback.message.bot)
    faces = await faces_repo.list_faces(callback.from_user.id)
    if not faces:
        await callback.answer("У тебя пока нет загруженных лиц.", show_alert=True)
        return
    lines = [
        "Сохранённые лица:",
        *[f"• {face.title or 'Без названия'} — #{face.id}" for face in faces],
        "\nУдалять или переиспользовать лица можно прямо здесь.",
    ]
    await callback.message.answer("\n".join(lines))
    await callback.answer()
