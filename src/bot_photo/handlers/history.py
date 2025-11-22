from __future__ import annotations

from aiogram import F, Router, types
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from ..keyboards import main_menu_keyboard
from ..utils import get_prompt_repo, get_sessions_repo, get_settings
from .sessions import STYLE_LABELS

router = Router(name="history")


@router.callback_query(lambda c: c.data == "menu:history")
async def show_history(callback: types.CallbackQuery) -> None:
    sessions_repo = get_sessions_repo(callback.message.bot)
    prompt_repo = get_prompt_repo(callback.message.bot)
    sessions = await sessions_repo.list_for_user(callback.from_user.id)
    prompts = await prompt_repo.list_for_user(callback.from_user.id)
    if not sessions and not prompts:
        await callback.message.answer(
            "Пока пусто. Запусти <Новая съёмка> или <Генерация по prompt>.",
            reply_markup=main_menu_keyboard(
                is_admin=callback.from_user.id in get_settings(callback.message.bot).admin_ids
            ),
        )
        await callback.answer()
        return
    await callback.answer()
    if sessions:
        await callback.message.answer("Недавние фотосессии:")
        for session in sessions:
            style_label = STYLE_LABELS.get(session.style, session.style)
            caption = f"{style_label} — {session.status}"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Открыть фото",
                            callback_data=f"history:session:{session.id}",
                        )
                    ]
                ]
            )
            await callback.message.answer(caption, reply_markup=keyboard)
    if prompts:
        lines = ["Недавние prompt-запросы:"]
        for record in prompts:
            lines.append(f"• {record.prompt[:40]}: - {record.status}")
        await callback.message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("history:session:"))
async def open_history_session(callback: types.CallbackQuery) -> None:
    session_id = int(callback.data.split(":")[2])
    sessions_repo = get_sessions_repo(callback.message.bot)
    session = await sessions_repo.get_by_id(session_id)
    if not session or session.user_id != callback.from_user.id:
        await callback.answer("Съёмка не найдена.", show_alert=True)
        return
    if not session.result_path:
        await callback.answer("Для этой съёмки нет результата.", show_alert=True)
        return
    style_label = STYLE_LABELS.get(session.style, session.style)
    await callback.message.answer_photo(
        FSInputFile(session.result_path),
        caption=f"{style_label} — готово",
    )
    await callback.answer()
