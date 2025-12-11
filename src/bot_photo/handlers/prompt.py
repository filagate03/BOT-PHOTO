from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from ..keyboards import main_menu_keyboard, prompt_templates_keyboard, sessions_keyboard
from ..models import PromptState
from ..services.nano_banana import NanoBananaAPIError
from ..utils import (
    get_file_storage,
    get_faces_repo,
    get_generation_client,
    get_prompt_repo,
    get_settings,
    get_token_service,
    get_users_repo,
)

router = Router(name="prompt")


@router.callback_query(lambda c: c.data == "menu:prompt")
async def prompt_home(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PromptState.waiting_face)
    await _ask_face(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("template:"))
async def template_selected(callback: types.CallbackQuery, state: FSMContext) -> None:
    template = callback.data.split(":", 1)[1]
    if template == "custom":
        await state.update_data(template=None)
        await callback.message.answer("Окей, пиши свою идею.")
    else:
        await state.update_data(template=template)
        await callback.message.answer("Супер! Добавь пару деталей (цвет, настроение).")
    await callback.answer()


@router.message(PromptState.waiting_text, F.text)
async def handle_prompt_text(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    template = data.get("template")
    face_id = data.get("face_id")
    prompt = message.text.strip()
    if not prompt:
        await message.answer("Нужно хотя бы несколько слов 🙂")
        return
    await _start_prompt_generation(message, state, prompt, template, face_id)


@router.callback_query(lambda c: c.data and c.data.startswith("prompt:face:"))
async def prompt_face_selected(callback: types.CallbackQuery, state: FSMContext) -> None:
    payload = callback.data.split(":", 2)[2]
    face_id = None if payload == "skip" else int(payload)
    await state.update_data(face_id=face_id)
    await state.set_state(PromptState.waiting_text)
    await callback.message.answer(
        "Опиши идею для картинки или выбери готовый шаблон ниже:",
        reply_markup=prompt_templates_keyboard(),
    )
    await callback.answer()


async def _start_prompt_generation(
    message: types.Message,
    state: FSMContext,
    prompt: str,
    template: str | None,
    face_id: int | None,
) -> None:
    try:
        settings = get_settings(message.bot)
        tokens = get_token_service(message.bot)
        users_repo = get_users_repo(message.bot)
        prompt_repo = get_prompt_repo(message.bot)
        user = await users_repo.get_by_id(message.from_user.id)
        if not user:
            await message.answer("Нет профиля. Нажми /start.")
            return
        if user.is_blocked:
            await message.answer("Аккаунт заблокирован.")
            return

        cost = settings.cost_per_prompt
        balance_before = await tokens.balance(user.telegram_id)
        if balance_before < cost:
            await message.answer(
                f"Недостаточно токенов: нужно {cost}, у тебя {balance_before}. Открой профиль и пополни баланс."
            )
            return

        balance_left = await tokens.spend(user.telegram_id, cost)
        await message.answer(f"Списано {cost} токенов. Остаток: {balance_left}.")
        record = await prompt_repo.create(
            user_id=user.telegram_id,
            prompt=prompt,
            template=template,
            status="processing",
            tokens_spent=cost,
        )
        status_line = "⏳ Генерируем по prompt..."
        if face_id:
            status_line = f"{status_line}\nРеференс лицо: #{face_id}"
        status_message = await message.answer(status_line)
        try:
            nano = get_generation_client(message.bot)
            face_urls: list[str] | None = None
            if face_id:
                face_urls = [await _ensure_face_file_by_id(message, face_id)]
            result = await nano.generate_prompt(prompt=prompt, template=template, face_urls=face_urls)
            bytes_image = _extract_image(result)
            storage = get_file_storage(message.bot)
            path_saved = await storage.save_generation(bytes_image)
            await prompt_repo.update_status(record.id, status="ready", result_path=path_saved.as_posix())
            await status_message.delete()
            await message.answer_photo(
                FSInputFile(path_saved),
                caption="Готово!",
                reply_markup=sessions_keyboard(),
            )
        except Exception as exc:  # pragma: no cover
            logging.exception("Failed to generate prompt")
            await tokens.add(user.telegram_id, cost)
            await prompt_repo.update_status(record.id, status="failed")
            await status_message.edit_text(f"Не вышло сгенерировать: {exc}")
        finally:
            await state.clear()
    except Exception as e:
        logging.exception("Error in _start_prompt_generation: %s", e)
        await message.answer("Произошла непредвиденная ошибка при обработке запроса.")


async def _ask_face(message: types.Message, user_id: int) -> None:
    faces_repo = get_faces_repo(message.bot)
    faces = await faces_repo.list_faces(user_id)
    lines = ["Выбери лицо для генерации по prompt:"]
    inline_keyboard = []
    if faces:
        for face in faces:
            title = face.title or f"Лицо #{face.id}"
            inline_keyboard.append(
                [types.InlineKeyboardButton(text=f"🧑‍🦰 {title}", callback_data=f"prompt:face:{face.id}")]
            )
    else:
        lines.append("У тебя пока нет сохранённых лиц. Можно продолжить без лица.")
    inline_keyboard.append([types.InlineKeyboardButton(text="➡️ Без лица", callback_data="prompt:face:skip")])
    inline_keyboard.append([types.InlineKeyboardButton(text="🏠 В меню", callback_data="menu:home")])
    await message.answer("\n".join(lines), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard))


async def _ensure_face_file_by_id(message: types.Message, face_id: int) -> str:
    faces_repo = get_faces_repo(message.bot)
    face = await faces_repo.get_by_id(face_id, message.from_user.id)
    if not face:
        raise RuntimeError("Лицо не найдено.")
    if face.file_path:
        path = Path(face.file_path)
        if path.exists():
            return path.as_posix()
    if not face.file_id:
        raise RuntimeError("Нет файла лица.")
    storage = get_file_storage(message.bot)
    new_path = await storage.save_face(message.bot, message.from_user.id, face.file_id)
    await faces_repo.update_file_path(face.id, message.from_user.id, new_path.as_posix())
    return new_path.as_posix()


def _extract_image(response: dict[str, Any]) -> bytes:
    data = _extract_inline_image(response)
    if data:
        return data
    images = response.get("images") or response.get("data")
    if images:
        raw = images[0]
        if isinstance(raw, dict):
            raw = raw.get("b64_json") or raw.get("content")
        if isinstance(raw, str):
            return base64.b64decode(raw)
    raise RuntimeError("Ответ модели пустой")


def _extract_inline_image(response: dict[str, Any]) -> bytes | None:
    candidates = response.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        data = _decode_inline_parts(parts)
        if data:
            return data
    contents = response.get("contents") or []
    for content in contents:
        parts = content.get("parts") or []
        data = _decode_inline_parts(parts)
        if data:
            return data
    return None


def _decode_inline_parts(parts: list[dict[str, Any]]) -> bytes | None:
    for part in parts:
        inline_data = part.get("inline_data") or part.get("inlineData")
        if isinstance(inline_data, dict) and inline_data.get("data"):
            return base64.b64decode(inline_data["data"])
    return None
