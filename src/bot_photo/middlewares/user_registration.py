from __future__ import annotations

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ..config import Settings
from ..repositories.users import UserRepository


class UserRegistrationMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings, users: UserRepository) -> None:
        super().__init__()
        self._settings = settings
        self._users = users

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        if from_user:
            user = await self._users.upsert_user(
                telegram_id=from_user.id,
                username=from_user.username,
                full_name=from_user.full_name,
                is_admin=from_user.id in self._settings.admin_ids,
                starting_tokens=self._settings.starting_tokens,
                hourly_limit=self._settings.hourly_limit,
            )
            data["user"] = user
        return await handler(event, data)