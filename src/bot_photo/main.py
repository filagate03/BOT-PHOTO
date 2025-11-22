from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from .config import Settings
from .db import Database
from .handlers import routers
from .middlewares import UserRegistrationMiddleware
from .repositories.faces import FaceRepository
from .repositories.prompts import PromptRepository
from .repositories.sessions import SessionRepository
from .repositories.usage import UsageRepository
from .repositories.users import UserRepository
from .services import ExamplesService, NanoBananaClient, RateLimitService, TokenService
from .storage import FileStorage
from .utils import init_context


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    settings = Settings()
    bot = Bot(
        settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    database = Database(settings.database_path)
    await database.connect()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    await database.run_script(schema_path)

    users_repo = UserRepository(database)
    faces_repo = FaceRepository(database)
    sessions_repo = SessionRepository(database)
    prompts_repo = PromptRepository(database)
    usage_repo = UsageRepository(database)

    file_storage = FileStorage(settings.faces_path, settings.sessions_path)
    examples_service = ExamplesService(settings.examples_path)
    examples_service.load()
    token_service = TokenService(users_repo)
    limit_service = RateLimitService(usage_repo, settings.hourly_limit)
    nano_client = NanoBananaClient(
        api_key=settings.nano_banana_api_key,
        base_url=settings.nano_banana_base_url,
        model=settings.nano_banana_model,
        fallback_model=settings.nano_banana_fallback_model,
    )

    init_context(
        settings=settings,
        database=database,
        repos={
            "users": users_repo,
            "faces": faces_repo,
            "sessions": sessions_repo,
            "prompts": prompts_repo,
            "usage": usage_repo,
        },
        services={
            "tokens": token_service,
            "limits": limit_service,
            "nano": nano_client,
            "examples": examples_service,
        },
        file_storage=file_storage,
    )

    dp.update.outer_middleware(UserRegistrationMiddleware(settings, users_repo))

    for router in routers:
        dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await nano_client.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
