from __future__ import annotations
import asyncio

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, FSInputFile

from ..keyboards import agreement_keyboard, main_menu_keyboard
from ..models import User
from ..models.states import AgreementState
from ..utils import get_settings, get_examples_service, get_users_repo

start_router = Router(name="start")
agreement_router = Router(name="agreement")


@start_router.message(CommandStart())
async def command_start(
    message: types.Message,
    state: FSMContext,
    user: User,
) -> None:
    """
    Главный обработчик команды /start.
    Отправляет приветственное сообщение, а затем либо запрашивает принятие
    соглашения, либо сразу открывает главное меню.
    """
    await state.clear()
    
    examples_service = get_examples_service(message.bot)
    await _send_welcome_message(message, examples_service)
    
    # Небольшая пауза для лучшего восприятия
    await asyncio.sleep(2)

    if user.agreement_accepted_at:
        await _send_main_menu(message, user)
    else:
        # Отправляем документы файлами
        policy_file = FSInputFile("privacy_policy.txt", filename="Политика конфиденциальности.txt")
        agreement_file = FSInputFile("user_agreement.txt", filename="Пользовательское соглашение.txt")
        await message.answer_document(policy_file)
        await message.answer_document(agreement_file)
        
        # Отправляем кнопку для принятия
        await message.answer(
            "Пожалуйста, ознакомьтесь с документами выше и примите условия, чтобы продолжить.",
            reply_markup=agreement_keyboard(),
        )
        await state.set_state(AgreementState.awaiting_agreement)


@agreement_router.callback_query(F.data == "agreement:accept", AgreementState.awaiting_agreement)
async def on_agreement_accept(
    callback: types.CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """
    Обрабатывает принятие соглашения.
    """
    await callback.answer("Спасибо! Добро пожаловать.")

    users_repo = get_users_repo(callback.bot)
    await users_repo.set_agreement_accepted(callback.from_user.id)
    await state.clear()
    
    # Удаляем сообщение с кнопкой, чтобы оно не мешалось
    await callback.message.delete()
    
    # Показываем главное меню
    await _send_main_menu(callback.message, user)


@start_router.callback_query(F.data == "menu:home")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    if callback.message.text:
         await callback.message.delete()
    
    await _send_main_menu(callback.message, user, is_edit=False)
    await callback.answer()


@start_router.callback_query(F.data == "menu:docs")
async def send_policies(callback: types.CallbackQuery) -> None:
    policy_file = FSInputFile("privacy_policy.txt", filename="privacy_policy.txt")
    agreement_file = FSInputFile("user_agreement.txt", filename="user_agreement.txt")
    await callback.message.answer_document(policy_file)
    await callback.message.answer_document(agreement_file)
    await callback.answer("Политика и соглашение всегда доступны здесь.")


async def _send_welcome_message(message: types.Message, examples_service) -> None:
    """Отправляет приветственное сообщение с примерами работ."""
    welcome_text = (
        "✨ Добро пожаловать в мир безграничных образов!\n\n"
        "Я — ваш личный AI-фотограф. Превратите любое фото в профессиональную фотосессию, просто загрузив его и выбрав стиль.\n\n"
        "Вот лишь несколько примеров того, что мы можем создать вместе:"
    )
    
    examples = list(examples_service.list_examples())[:3]
    
    # Используем первое изображение с Gemini_Generated_Image... или любой доступный
    if examples:
        special_example = next((e for e in examples if "Gemini_Generated" in e.file_path.name), examples[0])
        
        photo = FSInputFile(special_example.file_path)
        try:
            await message.answer_photo(photo, caption=welcome_text)
        except Exception:
            # Если Telegram даёт таймаут или не принимает файл, покажем текст без фото
            await message.answer(welcome_text + "\n\n(Пример не отправился, попробуй позже.)")
    else:
        await message.answer(welcome_text)


async def _send_main_menu(message: types.Message, user: User, is_edit: bool = True) -> None:
    """Отправляет главное меню."""
    text = (
        f"У вас <b>{user.tokens}</b> токенов.\n\n"
        "Выберите действие:"
    )
    keyboard = main_menu_keyboard(is_admin=user.is_admin)
    
    # В этой логике мы всегда отправляем новое сообщение для меню,
    # так как предыдущее - это либо пример, либо документы.
    await message.answer(text, reply_markup=keyboard)
