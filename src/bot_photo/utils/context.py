from __future__ import annotations

from typing import Any

from aiogram import Bot

from ..config import Settings
from ..db import Database
from ..repositories.faces import FaceRepository
from ..repositories.prompts import PromptRepository
from ..repositories.sessions import SessionRepository
from ..repositories.usage import UsageRepository
from ..repositories.users import UserRepository
from ..repositories.payments import PaymentRepository
from ..services.examples import ExamplesService
from ..services.limits import RateLimitService
from ..services.nano_banana import NanoBananaClient
from ..services.tokens import TokenService
from ..services.crypto_pay import CryptoPayService
from ..storage import FileStorage

_APP_CONTEXT: dict[str, Any] = {}


def init_context(
    *,
    settings: Settings,
    database: Database,
    repos: dict[str, Any],
    services: dict[str, Any],
    file_storage: FileStorage,
) -> None:
    _APP_CONTEXT.update(
        {
            "settings": settings,
            "database": database,
            "repos": repos,
            "services": services,
            "file_storage": file_storage,
        }
    )


def _get_context(key: str) -> Any:
    if key not in _APP_CONTEXT:
        raise RuntimeError(f"Context key '{key}' is not initialized")
    return _APP_CONTEXT[key]


def get_settings(bot: Bot | None = None) -> Settings:
    return _get_context("settings")


def get_database(bot: Bot | None = None) -> Database:
    return _get_context("database")


def get_repo(bot: Bot | None, name: str) -> Any:
    return _get_context("repos")[name]


def get_service(bot: Bot | None, name: str) -> Any:
    return _get_context("services")[name]


def get_users_repo(bot: Bot | None) -> UserRepository:
    return get_repo(bot, "users")


def get_faces_repo(bot: Bot | None) -> FaceRepository:
    return get_repo(bot, "faces")


def get_sessions_repo(bot: Bot | None) -> SessionRepository:
    return get_repo(bot, "sessions")


def get_prompt_repo(bot: Bot | None) -> PromptRepository:
    return get_repo(bot, "prompts")


def get_usage_repo(bot: Bot | None) -> UsageRepository:
    return get_repo(bot, "usage")


def get_payments_repo(bot: Bot | None) -> PaymentRepository:
    return get_repo(bot, "payments")


def get_token_service(bot: Bot | None) -> TokenService:
    return get_service(bot, "tokens")


def get_limit_service(bot: Bot | None) -> RateLimitService:
    return get_service(bot, "limits")


def get_generation_client(bot: Bot | None) -> NanoBananaClient:
    return get_service(bot, "nano")


def get_examples_service(bot: Bot | None) -> ExamplesService:
    return get_service(bot, "examples")


def get_file_storage(bot: Bot | None) -> FileStorage:
    return _get_context("file_storage")


def get_crypto_pay_service(bot: Bot | None) -> CryptoPayService:
    return get_service(bot, "crypto_pay")
