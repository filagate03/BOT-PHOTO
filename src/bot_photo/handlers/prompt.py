from __future__ import annotations

import base64
import logging
from typing import Any

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from ..keyboards import main_menu_keyboard, prompt_templates_keyboard, sessions_keyboard
from ..models import PromptState
from ..services.nano_banana import NanoBananaAPIError
from ..utils import (
    get_file_storage,
    get_generation_client,
    get_prompt_repo,
    get_settings,
    get_token_service,
    get_users_repo,
)

router = Router(name="prompt")


@router.callback_query(lambda c: c.data == "menu:prompt")
async def prompt_home(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PromptState.waiting_text)
    await callback.message.answer(
        "Опиши идею для картинки или выбери готовый шаблон ниже:",
        reply_markup=prompt_templates_keyboard(),
    )
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
    prompt = message.text.strip()
    if not prompt:
        await message.answer("Нужно хотя бы несколько слов 🙂")
        return
    await _start_prompt_generation(message, state, prompt, template)


async def _start_prompt_generation(
    message: types.Message,
    state: FSMContext,
    prompt: str,
    template: str | None,
) -> None:
    await message.answer("Entering _start_prompt_generation")
    try:
        logging.debug("message.from_user in _start_prompt_generation: %s", message.from_user)
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
        logging.debug("Tokens before prompt spend user=%s balance=%s cost=%s", user.telegram_id, balance_before, cost)
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
        status_message = await message.answer("⏳ Генерируем по prompt...")
        try:
            nano = get_generation_client(message.bot)
            result = await nano.generate_prompt(prompt=prompt, template=template)
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
