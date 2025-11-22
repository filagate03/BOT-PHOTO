from __future__ import annotations

from aiogram import Router, types
from aiogram.types import FSInputFile

from ..keyboards import main_menu_keyboard
from ..utils import get_examples_service, get_settings, get_users_repo

router = Router(name="examples")


@router.callback_query(lambda c: c.data == "menu:examples")
async def show_examples(callback: types.CallbackQuery) -> None:
    bot = callback.message.bot
    examples_service = get_examples_service(bot)
    examples = list(examples_service.list_examples())
    if not examples:
        await callback.message.answer(
            "Примеры появятся чуть позже. Пока можно загрузить свои фото и выбрать стиль.",
            reply_markup=main_menu_keyboard(
                is_admin=callback.from_user.id in get_settings(bot).admin_ids
            ),
        )
        await callback.answer()
        return
    await callback.answer("Показываю стили…", show_alert=False)
    shown_any = False
    for example in examples:
        if not example.file_path.exists():
            continue
        shown_any = True
        input_file = FSInputFile(example.file_path)
        caption = f"{example.title}\n{example.caption}\n\nНажми «Давай так же!»"
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Давай так же!", callback_data=f"style:{example.style}"
                    )
                ]
            ]
        )
        await callback.message.answer_photo(
            input_file,
            caption=caption,
            reply_markup=keyboard,
        )
    await get_users_repo(bot).set_demo_viewed(callback.from_user.id)
    if not shown_any:
        await callback.message.answer(
            "Файлы-примеры ещё не загружены, но можно начинать собственную фотосессию.",
            reply_markup=main_menu_keyboard(
                is_admin=callback.from_user.id in get_settings(bot).admin_ids
            ),
        )
        return
    await callback.message.answer(
        "Готов сделать свою фотосессию?",
        reply_markup=main_menu_keyboard(
            is_admin=callback.from_user.id in get_settings(bot).admin_ids
        ),
    )
