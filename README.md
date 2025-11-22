# Telegram bot "bot photo"

Aiogram 3.x bot that helps users create realistic photo shoots and prompt-based images via Google Gemini (nano banana aka `gemini-2.5-flash-image-preview`).

## Features
- Main menu with 📸 Новая фотосессия, 🔍 Примеры стилей, ✨ Генерация по prompt, 👤 Профиль, 🖼 Мои фотосессии, ⚙️ Админка.
- Photo sessions: pick a style, upload 1–3 faces (or reuse saved ones), optionally describe the vibe, spend tokens, get media.
- Prompt-only generation with templates/custom text.
- Profile with balance, saved faces, hourly limits, manual top-up instructions.
- History of previous sessions/prompts.
- Simple admin UI (stats, tokens, bans, examples).
- SQLite + local media storage (faces/sessions folders).

## Project layout
```
├── README.md
├── requirements.txt
├── .env / .env.example
├── repo/examples/        # static showcase media referenced in manifest.json
├── src/bot_photo/
│   ├── config.py         # pydantic settings
│   ├── main.py           # entry point
│   ├── db/               # schema + async wrapper
│   ├── handlers/         # aiogram routers
│   ├── keyboards/        # inline keyboards
│   ├── middlewares/      # auto-registration
│   ├── models/           # dataclasses + FSM states
│   ├── repositories/     # SQLite access
│   ├── services/         # Gemini client, tokens, limits, examples
│   ├── storage/          # file storage helper
│   └── utils/            # DI helpers
└── storage/, var/        # created automatically
```

## Setup
1. Create virtualenv & install deps:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` → `.env` and configure:
   - `TELEGRAM_BOT_TOKEN` — BotFather token.
   - `NANO_BANANA_API_KEY` — Google Gemini API key (from AI Studio, looks like `AIza...`).
   - `NANO_BANANA_BASE_URL` — defaults to `https://generativelanguage.googleapis.com/v1beta`.
   - `NANO_BANANA_MODEL` — `gemini-2.5-flash-image-preview`.
   - `NANO_BANANA_FALLBACK_MODEL` — leave empty if нужно только preview.
   - Update DB/storage paths if desired.
3. Put showcase images into `repo/examples` and describe them in `manifest.json` (style/title/caption/file).

## Gemini integration
- `NanoBananaClient` now calls `POST https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent` with the provided API key (header `x-goog-api-key`).
- Faces are attached as inline parts (base64), prompt text is appended afterwards.
- Safety filters are disabled via `safetySettings` so фотосессии не блокируются guardrail’ами.
- The client automatically detects guardrail/model errors and (optionally) tries a fallback model if you specify one.
- `_extract_first_image` / `_extract_image` decode Google’s `inline_data` so бот получает base64 изображения из `candidates[].content.parts`.

## Running
```bash
python -m src.bot_photo.main
```
Keep the terminal alive; stopping it ends polling.

## Admin commands
- `/addtokens <user_id> <amount>`
- `/ban <user_id>` / `/unban <user_id>`

## Next steps
- Add proper billing (Cloud Payments, ЮKassa, etc.).
- Move heavy generation to a job queue and switch aiogram to webhooks.
- Add UI to delete/rename faces.
- Cover services/repos with tests + CI.
