from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from ..keyboards import faces_keyboard, main_menu_keyboard, orientation_keyboard, sessions_keyboard, styles_keyboard
from ..models import PhotoSessionState
from ..utils import (
    get_examples_service,
    get_faces_repo,
    get_file_storage,
    get_generation_client,
    get_sessions_repo,
    get_settings,
    get_token_service,
    get_users_repo,
)

SESSION_STYLES: list[tuple[str, str]] = [
    ("haute_couture_runway", "Показ haute couture"),
    ("red_carpet_premiere", "Красная дорожка премьеры"),
    ("eiffel_tower_evening", "У Эйфелевой башни вечером"),
    ("santorini_sunrise", "Санторини на рассвете"),
    ("dubai_rooftop", "Дубай, вид с крыши"),
    ("tokyo_neon_street", "Токио, неоновая улица"),
    ("new_york_rooftop", "Нью-Йорк, съёмка на крыше"),
    ("milan_fashion_week", "Милан, закулисье Fashion Week"),
    ("paris_sidewalk_cafe", "Париж, уличное кафе"),
    ("london_rain_editorial", "Лондон, дождевой editorial"),
    ("yacht_deck_sunset", "Яхта на закате"),
    ("private_jet_cabin", "Каюта частного джета"),
    ("luxury_hotel_suite", "Люкс в отеле"),
    ("art_gallery_minimal", "Минималистичная галерея"),
    ("royal_ballroom", "Королевский бальный зал"),
    ("mediterranean_villa", "Вилла на Средиземном море"),
    ("alpine_ski_chalet", "Альпийское шале"),
    ("desert_supercar", "Суперкар в пустыне"),
    ("vineyard_golden_hour", "Виноградник на закате"),
    ("maldives_beach", "Мальдивы, рассвет на пляже"),
    ("tropical_rainforest_mist", "Туманный тропический лес"),
    ("snowy_forest_coat", "Заснеженный лес, пальто"),
    ("urban_loft_window", "Лофт у панорамных окон"),
    ("marble_spa_retreat", "Мраморный спа"),
    ("helipad_twilight", "Вертолётная площадка в сумерках"),
    ("rooftop_pool_party", "Вечеринка у бассейна на крыше"),
    ("seaside_boardwalk", "Прогулка у моря"),
    ("bridal_editorial", "Бридал-эдиториал"),
    ("street_style_editorial", "Street style съёмка"),
    ("art_deco_suite", "Ар-деко апартаменты"),
    ("museum_hall", "Зал музея"),
    ("cozy_chalet_fireplace", "Шале у камина"),
    ("greenhouse_bloom", "Оранжерея в цвету"),
    ("opera_house_grand_staircase", "Лестница оперного театра"),
    ("venice_grand_canal", "Венеция, Гранд-канал"),
    ("moroccan_riad", "Марокканский риад"),
    ("bali_rice_terrace", "Бали, рисовые террасы"),
    ("taj_mahal_dawn", "Тадж-Махал на рассвете"),
    ("safari_lodge", "Сафари-лодж"),
    ("renaissance_courtyard", "Двор эпохи Ренессанса"),
    ("hollywood_backlot", "Павильон Голливуда"),
    ("golden_hour_garden", "Сад в золотой час"),
    ("fantasy_world", "Фэнтези-мир"),
    ("cyberpunk_city", "Киберпанк-город"),
    ("sci_fi_spaceport", "Научно-фантастический космопорт"),
    ("steampunk_city", "Стимпанк-город"),
    ("mythic_forest", "Мифический лес"),
    ("celestial_palace", "Небесный дворец"),
    ("underwater_atlantis", "Подводная Атлантида"),
    ("neon_dreamscape", "Неоновый сон"),
    ("dragon_mountain_keep", "Крепость на горе драконов"),
    ("enchanted_castle", "Заколдованный замок"),
    ("floating_sky_islands", "Парящие острова в небе"),
    ("aurora_ice_palace", "Ледяной дворец и северное сияние"),
    ("ancient_ruins_magic", "Древние руины с магией"),
    ("galactic_couture", "Галактический кутюр"),
    ("futuristic_runway", "Футуристический подиум"),
    ("phoenix_rebirth", "Возрождение феникса"),
    ("lunar_base_ceremony", "Церемония на лунной базе"),
    ("frost_giant_peak", "Пик ледяных великанов"),
]
STYLE_LABELS = dict(SESSION_STYLES)
MAX_FACES = 10

router = Router(name="sessions")


def _face_progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="faces:done")],
            [InlineKeyboardButton(text="📤 Загрузить лицо", callback_data="faces:upload")],
            [InlineKeyboardButton(text="🧑‍🦰 Выбрать сохранённое", callback_data="faces:list")],
            [InlineKeyboardButton(text="🗑 Удалить лицо", callback_data="faces:delete_list")],
        ]
    )


def _prompt_controls_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Сгенерировать без описания", callback_data="prompt:default")],
            [InlineKeyboardButton(text="🏠 Домой", callback_data="menu:home")],
        ]
    )

def _prompt_controls_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Сделать как в примере", callback_data="prompt:default")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:home")],
        ]
    )


@router.callback_query(lambda c: c.data == "menu:new_session")
async def start_session(callback: types.CallbackQuery, state: FSMContext) -> None:
    settings = get_settings(callback.message.bot)
    user = await _get_or_create_user(callback.message.bot, callback.from_user)
    if user and user.is_blocked:
        await callback.answer("Аккаунт заблокирован. Напиши в поддержку.", show_alert=True)
        return

    await state.set_state(PhotoSessionState.choosing_style)
    await callback.message.answer(
        (
            "📸 Новая фотосессия\n"
            f"• Стоимость запуска: {settings.cost_per_session} токенов\n"
            f"• Баланс: {user.tokens if user else 0} токенов\n\n"
            "Шаг 1: выбери стиль.\n"
            "Шаг 2: добавь до 10 лиц.\n"
            "Шаг 3: опиши кадр или жми «Сгенерировать без описания»."
        )
    )
    await callback.message.answer("Выбери стиль:", reply_markup=styles_keyboard(SESSION_STYLES))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("style:"))
async def on_style_chosen(callback: types.CallbackQuery, state: FSMContext) -> None:
    style = callback.data.split(":", 1)[1]
    await state.update_data(style=style, orientation="vertical", faces=[], pending_face_ids=[])
    await state.set_state(PhotoSessionState.waiting_face)

    await callback.message.delete()
    await callback.message.answer(
        f"Стиль «{style}» выбран. Пришли 1–10 фото лиц или выбери сохранённые.",
        reply_markup=faces_keyboard(),
    )

    examples = get_examples_service(callback.message.bot)
    preview = examples.get_by_style(style)
    if preview and preview.file_path.exists():
        await callback.message.answer_photo(
            FSInputFile(preview.file_path),
            caption=f"Пример стиля «{preview.title}». Добавь своё лицо и жми «Готово».",
        )
    await callback.answer()


@router.callback_query(PhotoSessionState.choosing_orientation, lambda c: c.data and c.data.startswith("orientation:"))
async def on_orientation_chosen(callback: types.CallbackQuery, state: FSMContext) -> None:
    orientation = callback.data.split(":", 1)[1]
    await state.update_data(orientation=orientation, faces=[], pending_face_ids=[])
    await state.set_state(PhotoSessionState.waiting_face)

    data = await state.get_data()
    style = data.get("style")
    
    await callback.message.delete()
    await callback.message.answer(
        f"Стиль «{style}» и ориентация «{orientation}» выбраны.\nПришлите 1–3 фото лица или выберите сохранённые.",
        reply_markup=faces_keyboard(),
    )
    
    examples = get_examples_service(callback.message.bot)
    preview = examples.get_by_style(style)
    if preview and preview.file_path.exists():
        await callback.message.answer_photo(
            FSInputFile(preview.file_path),
            caption=f"Так выглядит стиль «{preview.title}». Добавьте своё лицо и жмите «✅ Готово».",
        )
    await callback.answer()


@router.callback_query(PhotoSessionState.waiting_face, lambda c: c.data == "faces:upload")
async def face_upload_prompt(callback: types.CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Жду 1–3 фото лица. Лучше светлое селфи без очков и фильтров.")


@router.callback_query(PhotoSessionState.waiting_face, lambda c: c.data == "faces:list")
async def show_faces(callback: types.CallbackQuery, state: FSMContext) -> None:
    faces_repo = get_faces_repo(callback.message.bot)
    faces = await faces_repo.list_faces(callback.from_user.id)
    if not faces:
        await callback.answer("Сохранённых лиц нет.", show_alert=True)
        return
    inline_keyboard = []
    for face in faces:
        title = face.title or f"Лицо #{face.id}"
        inline_keyboard.append(
            [
                InlineKeyboardButton(text=f"✅ {title}", callback_data=f"faces:use:{face.id}"),
                InlineKeyboardButton(text=f"🗑 {title}", callback_data=f"faces:delete:{face.id}"),
            ]
        )
    inline_keyboard.append([InlineKeyboardButton(text="🏠 Домой", callback_data="menu:home")])
    await callback.message.answer(
        "Выбери лицо из сохранённых:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard),
    )
    await callback.answer()


@router.callback_query(PhotoSessionState.waiting_face, lambda c: c.data and c.data.startswith("faces:use:"))
async def use_saved_face(callback: types.CallbackQuery, state: FSMContext) -> None:
    face_id = int(callback.data.split(":")[2])
    faces_repo = get_faces_repo(callback.message.bot)
    faces = await faces_repo.list_faces(callback.from_user.id)
    selected = next((face for face in faces if face.id == face_id), None)
    if not selected:
        await callback.answer("Такого лица нет.", show_alert=True)
        return
    data = await state.get_data()
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    if len(faces_state) >= MAX_FACES:
        await callback.answer(f"Можно добавить не более {MAX_FACES} лиц в одну фотосессию.", show_alert=True)
        return
    faces_state.append(
        {
            "face_id": selected.id,
            "file_path": selected.file_path,
            "file_id": selected.file_id,
        }
    )
    await state.update_data(faces=faces_state)
    name = selected.title or f"Лицо #{selected.id}"
    await callback.message.answer(
        f"Добавил «{name}» ({len(faces_state)}/{MAX_FACES}). Нажми «✅ Готово», когда закончишь.",
        reply_markup=_face_progress_keyboard(),
    )
    await callback.answer("Готово", show_alert=False)


@router.callback_query(PhotoSessionState.waiting_face, lambda c: c.data and c.data.startswith("faces:delete:"))
async def delete_face(callback: types.CallbackQuery, state: FSMContext) -> None:
    face_id = int(callback.data.split(":")[2])
    faces_repo = get_faces_repo(callback.message.bot)
    await faces_repo.delete_face(face_id, callback.from_user.id)
    data = await state.get_data()
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    faces_state = [f for f in faces_state if f.get("face_id") != face_id]
    await state.update_data(faces=faces_state)
    await callback.answer("Лицо удалено.", show_alert=False)
    await callback.message.answer("Удалено. Загрузи новое или выбери другое.", reply_markup=_face_progress_keyboard())


@router.callback_query(PhotoSessionState.waiting_face, lambda c: c.data == "faces:done")
async def faces_done(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pending_face_ids: list[int] = data.get("pending_face_ids", [])
    if pending_face_ids:
        await callback.answer("Сначала дай названия загруженным лицам (отправь текст).", show_alert=True)
        return
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    if not faces_state:
        await callback.answer("Нужно добавить хотя бы одно лицо.", show_alert=True)
        return
    await state.set_state(PhotoSessionState.waiting_prompt)
    await callback.message.delete()
    await callback.message.answer(
        "Отлично! Добавь описание (сцена, одежда, настроение) или нажми «✨ Сгенерировать без описания».",
        reply_markup=_prompt_controls_keyboard(),
    )
    await callback.answer()


@router.message(PhotoSessionState.waiting_face, F.photo)
async def handle_face_photo(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    if len(faces_state) >= MAX_FACES:
        await message.answer(f"Фото достаточно (макс. {MAX_FACES}). Нажми «✅ Готово».", reply_markup=_face_progress_keyboard())
        return

    photo = message.photo[-1]
    storage = get_file_storage(message.bot)
    file_path = await storage.save_face(message.bot, message.from_user.id, photo.file_id)
    faces_repo = get_faces_repo(message.bot)
    new_face = await faces_repo.add_face(
        user_id=message.from_user.id,
        title=None,
        file_id=photo.file_id,
        file_path=file_path.as_posix(),
    )
    faces_state.append(
        {
            "face_id": new_face.id,
            "file_path": file_path.as_posix(),
            "file_id": photo.file_id,
        }
    )
    pending_face_ids: list[int] = data.get("pending_face_ids", [])
    pending_face_ids.append(new_face.id)
    await state.update_data(faces=faces_state, pending_face_ids=pending_face_ids)
    await message.answer(
        f"Фото ({len(faces_state)}/{MAX_FACES}) добавлено. Как его назвать? (или отправь «-», чтобы пропустить)",
        reply_markup=_face_progress_keyboard(),
    )


@router.message(PhotoSessionState.waiting_face, F.text)
async def handle_face_name(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    pending_face_ids: list[int] = data.get("pending_face_ids", [])
    if not pending_face_ids:
        await message.answer("Сначала загрузите лицо, затем отправьте его название.", reply_markup=_face_progress_keyboard())
        return

    face_id = pending_face_ids.pop(0)
    title = message.text.strip()
    if title == "-":
        title = None

    faces_repo = get_faces_repo(message.bot)
    await faces_repo.update_title(face_id=face_id, user_id=message.from_user.id, title=title)
    await state.update_data(pending_face_ids=pending_face_ids)

    if title:
        await message.answer(f"Готово! Лицо <{title}> сохранено.")
    else:
        await message.answer("Лицо сохранено без названия.")

    if not pending_face_ids:
        await message.answer("Все лица обработаны. Добавь описание или жми «✨ Сгенерировать без описания».", reply_markup=_prompt_controls_keyboard())
        await state.set_state(PhotoSessionState.waiting_prompt)
@router.callback_query(PhotoSessionState.waiting_prompt, lambda c: c.data == "prompt:default")
async def handle_prompt_default(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    style = data.get("style")
    orientation = data.get("orientation")
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    if not style or not faces_state or not orientation:
        await callback.answer("Начни фотосессию заново.", show_alert=True)
        await state.clear()
        return
    await _start_generation(callback.message, state, style, orientation, faces_state, None)
    await callback.answer()


@router.message(PhotoSessionState.waiting_prompt, F.text)
async def handle_session_prompt(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    style = data.get("style")
    orientation = data.get("orientation")
    faces_state: list[dict[str, Any]] = data.get("faces", [])
    if not style or not faces_state or not orientation:
        await message.answer("Начни фотосессию заново.")
        await state.clear()
        return
    prompt = message.text.strip()
    if not prompt:
        await message.answer("Нужно хотя бы несколько слов 🙂")
        return
    await _start_generation(message, state, style, orientation, faces_state, prompt)



async def _start_generation(
    message: types.Message,
    state: FSMContext,
    style: str,
    orientation: str,
    faces: list[dict[str, Any]],
    prompt: str | None,
) -> None:
    settings = get_settings(message.bot)
    token_service = get_token_service(message.bot)
    users_repo = get_users_repo(message.bot)
    sessions_repo = get_sessions_repo(message.bot)
    examples_service = get_examples_service(message.bot)
    user = await _get_or_create_user(message.bot, message.from_user)
    if not user:
        await message.answer("Не удалось получить профиль. Нажми /start.")
        return

    if user.is_blocked:
        await message.answer("Аккаунт заблокирован. Напиши в поддержку.")
        return

    cost = settings.cost_per_session
    balance_before = await token_service.balance(user.telegram_id)
    if balance_before < cost:
        await message.answer(
            f"Недостаточно токенов: нужно {cost}, у тебя {balance_before}. Открой профиль и пополни баланс."
        )
        return

    balance_left = await token_service.spend(user.telegram_id, cost)
    await message.answer(f"Списано {cost} токенов. Остаток: {balance_left}.")
    session = await sessions_repo.create_session(
        user_id=user.telegram_id,
        style=style,
        prompt=prompt,
        status="processing",
        tokens_spent=cost,
    )
    await state.set_state(PhotoSessionState.processing)

    status_message = await message.answer("⏳ Генерируем, подожди...")
    image_bytes: bytes | None = None
    error_text: str | None = None
    session_status = "ready"
    nano = get_generation_client(message.bot)
    try:
        face_paths = [await _ensure_face_file(message, face) for face in faces]
        result = await nano.generate_photosession(
            style=style,
            prompt=prompt,
            orientation=orientation,
            face_urls=face_paths,
        )
        image_bytes = _extract_first_image(result)
    except Exception as exc:  # pragma: no cover
        fallback = examples_service.get_by_style(style)
        if fallback and fallback.file_path.exists():
            image_bytes = fallback.file_path.read_bytes()
            error_text = (
                "Основная генерация недоступна, показан эталон из примеров. "
                "Токены возвращены."
            )
            session_status = "fallback"
            await token_service.add(user.telegram_id, cost)
        else:
            await token_service.add(user.telegram_id, cost)
            await sessions_repo.update_status(session.id, status="failed")
            await status_message.edit_text(f"Не вышло сгенерировать: {exc}")
            await state.clear()
            return

    storage = get_file_storage(message.bot)
    image_path = await storage.save_generation(image_bytes)
    await sessions_repo.update_status(
        session_id=session.id,
        status=session_status,
        result_path=image_path.as_posix(),
    )
    await status_message.delete()
    await message.answer_photo(
        FSInputFile(image_path),
        caption="Готово! Вот твоя съёмка. Хочешь ещё? Запусти новую сцену.",
        reply_markup=sessions_keyboard(),
    )
    if error_text:
        await message.answer(error_text)
    await state.clear()

async def _ensure_face_file(message: types.Message, face: dict[str, Any]) -> str:
    path_value = face.get("file_path")
    if path_value:
        candidate = Path(path_value)
        if candidate.exists():
            return candidate.as_posix()
    file_id = face.get("file_id")
    if not file_id:
        raise RuntimeError("Не удалось получить файл лица.")
    storage = get_file_storage(message.bot)
    new_path = await storage.save_face(message.bot, message.from_user.id, file_id)
    faces_repo = get_faces_repo(message.bot)
    if face.get("face_id"):
        await faces_repo.update_file_path(face["face_id"], message.from_user.id, new_path.as_posix())
    face["file_path"] = new_path.as_posix()
    return new_path.as_posix()


def _extract_first_image(response: dict[str, Any]) -> bytes:
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
        if isinstance(raw, bytes):
            return raw
    raise RuntimeError("Nano banana вернул пустой результат")


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


@router.callback_query(lambda c: c.data == "session:share")
async def share_last_session(callback: types.CallbackQuery) -> None:
    sessions_repo = get_sessions_repo(callback.message.bot)
    sessions = await sessions_repo.list_for_user(callback.from_user.id, limit=1)
    if not sessions:
        await callback.answer("Пока нет готовых съёмок.", show_alert=True)
        return
    session = sessions[0]
    if not session.result_path:
        await callback.answer("У последней съёмки нет файла.", show_alert=True)
        return
    style_label = STYLE_LABELS.get(session.style, session.style)
    await callback.message.answer_photo(
        FSInputFile(session.result_path),
        caption=f"{style_label}\nПерешли это фото другу или сохрани себе.",
        reply_markup=sessions_keyboard(),
    )
    await callback.answer("Фото отправлено. Просто пересылай его дальше.")

async def _get_or_create_user(bot: types.Bot, from_user: types.User):
    users_repo = get_users_repo(bot)
    user = await users_repo.get_by_id(from_user.id)
    if user:
        return user
    settings = get_settings(bot)
    return await users_repo.upsert_user(
        telegram_id=from_user.id,
        username=from_user.username,
        full_name=from_user.full_name,
        is_admin=from_user.id in settings.admin_ids,
        starting_tokens=settings.starting_tokens,
        hourly_limit=settings.hourly_limit,
    )
