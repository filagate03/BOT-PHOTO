from __future__ import annotations

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from ..keyboards import admin_cancel_keyboard, admin_main_keyboard, admin_manage_user_keyboard
from ..models import AdminState, User
from ..utils import get_database, get_settings, get_token_service, get_users_repo

router = Router(name="admin")


# Helper to send admin main menu, adapting to Message or CallbackQuery
async def _send_admin_main_menu(entity: types.Message | types.CallbackQuery, user: User) -> None:
    text = "⚙️ Админка"
    keyboard = admin_main_keyboard()

    if isinstance(entity, types.CallbackQuery):
        await entity.message.edit_text(text, reply_markup=keyboard)
        await entity.answer()
    else:
        await entity.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "menu:admin")
async def admin_home_callback(callback: types.CallbackQuery, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Недоступно", show_alert=True)
        return
    await _send_admin_main_menu(callback, user)


@router.message(Command("admin")) # Allow direct command access
async def admin_home_command(message: types.Message, user: User) -> None:
    if not user.is_admin:
        await message.answer("Недоступно")
        return
    await _send_admin_main_menu(message, user)


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: types.CallbackQuery, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    db = get_database(callback.message.bot)
    users_count = await db.fetchval("SELECT COUNT(*) FROM users")
    sessions = await db.fetchval("SELECT COUNT(*) FROM sessions")
    prompts = await db.fetchval("SELECT COUNT(*) FROM prompt_generations")
    text = (
        "📊 Статистика\n"
        f"Пользователей: {users_count or 0}\n"
        f"Фотосессий: {sessions or 0}\n"
        f"Prompt генераций: {prompts or 0}"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin:examples")
async def admin_examples_hint(callback: types.CallbackQuery, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Загрузи файлы в repo/examples и обнови manifest.json.")
    await callback.answer()


@router.callback_query(F.data == "admin:bans")
async def admin_bans(callback: types.CallbackQuery, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Для бана используй команду /ban <code>&lt;user_id&gt;</code>. Для разбана — /unban <code>&lt;user_id&gt;</code>.")
    await callback.answer()


# region Give Tokens
@router.callback_query(F.data == "admin:give_tokens") # From main admin menu
async def admin_give_tokens_start(callback: types.CallbackQuery, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.token_input_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя, которому хотите выдать токены:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminState.token_input_user_id)
async def admin_give_tokens_user_id(message: types.Message, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await message.answer("Нет доступа.")
        await state.clear()
        return
    try:
        target_user_id = int(message.text)
        await state.update_data(target_user_id=target_user_id)
        await state.set_state(AdminState.token_input_amount)
        await message.answer(
            f"Пользователь <code>{target_user_id}</code> выбран. Теперь введите количество токенов:",
            reply_markup=admin_cancel_keyboard(),
        )
    except ValueError:
        await message.answer("Неверный ID пользователя. Введите число.")


@router.message(AdminState.token_input_amount)
async def admin_give_tokens_amount(message: types.Message, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await message.answer("Нет доступа.")
        await state.clear()
        return
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError("Количество токенов должно быть положительным числом.")
        
        data = await state.get_data()
        target_user_id = data.get("target_user_id")
        if not target_user_id:
            await message.answer("Произошла ошибка. Начните заново.")
            await state.clear()
            return
        
        token_service = get_token_service(message.bot)
        await token_service.add(target_user_id, amount)
        
        await message.answer(f"Начислено {amount} токенов пользователю <code>{target_user_id}</code>.")
        await state.clear()
        await _send_admin_main_menu(message, user) # Back to admin main menu
    except ValueError as e:
        await message.answer(f"Неверное количество токенов. {e}. Введите число.")
# endregion


# region Manage Admins
@router.callback_query(F.data == "admin:manage_admins")
async def admin_manage_admins_start(callback: types.CallbackQuery, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.admin_input_user_id)
    await callback.message.edit_text(
        "Введите ID пользователя для управления админ-правами:",
        reply_markup=admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminState.admin_input_user_id)
async def admin_manage_admins_user_id(message: types.Message, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await message.answer("Нет доступа.")
        await state.clear()
        return
    try:
        target_user_id = int(message.text)
        users_repo = get_users_repo(message.bot)
        target_user = await users_repo.get_by_id(target_user_id)
        
        if not target_user:
            await message.answer(f"Пользователь с ID <code>{target_user_id}</code> не найден.")
            return

        await state.update_data(target_user_id=target_user_id)
        await message.answer(
            f"Пользователь <code>{target_user_id}</code> (Админ: {target_user.is_admin}). Выберите действие:",
            reply_markup=admin_manage_user_keyboard(target_user_id, target_user.is_admin),
        )
    except ValueError:
        await message.answer("Неверный ID пользователя. Введите число.")


@router.callback_query(F.data.startswith("admin_manage:"), AdminState.admin_input_user_id)
async def admin_manage_admins_action(callback: types.CallbackQuery, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    action = parts[1] # 'grant' or 'revoke'
    target_user_id = int(parts[2])

    users_repo = get_users_repo(callback.bot)
    
    if action == "grant":
        await users_repo.set_admin_status(target_user_id, True)
        await callback.message.edit_text(f"Пользователь <code>{target_user_id}</code> назначен админом.")
    elif action == "revoke":
        await users_repo.set_admin_status(target_user_id, False)
        await callback.message.edit_text(f"Пользователь <code>{target_user_id}</code> разжалован.")
    
    await state.clear()
    await _send_admin_main_menu(callback, user) # Back to admin main menu
    await callback.answer()
# endregion


# region Ban/Unban - existing logic using commands
@router.message(Command("addtokens"))
async def command_add_tokens_legacy(message: types.Message, user: User) -> None:
    if not user.is_admin:
        await message.answer("Недоступно")
        return
    await message.answer("Используйте меню админки для выдачи токенов.", reply_markup=admin_main_keyboard())


@router.message(Command("ban"))
async def command_ban(message: types.Message, user: User) -> None:
    if not user.is_admin:
        await message.answer("Недоступно")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /ban <code>&lt;user_id&gt;</code>")
        return
    try:
        target = int(parts[1])
        users = get_users_repo(message.bot)
        await users.set_blocked(target, True)
        await message.answer(f"Пользователь <code>{target}</code> заблокирован.")
    except ValueError:
        await message.answer("Неверный ID пользователя. Введите число.")


@router.message(Command("unban"))
async def command_unban(message: types.Message, user: User) -> None:
    if not user.is_admin:
        await message.answer("Недоступно")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /unban <code>&lt;user_id&gt;</code>")
        return
    try:
        target = int(parts[1])
        users = get_users_repo(message.bot)
        await users.set_blocked(target, False)
        await message.answer(f"Пользователь <code>{target}</code> разблокирован.")
    except ValueError:
        await message.answer("Неверный ID пользователя. Введите число.")
# endregion


# region Cancel
@router.callback_query(F.data == "admin:cancel", AdminState()) # Listen to all AdminStates
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext, user: User) -> None:
    if not user.is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Операция отменена.", reply_markup=admin_main_keyboard())
    await callback.answer()
# endregion
