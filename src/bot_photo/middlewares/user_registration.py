from __future__ import annotations

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram import types
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
            if not user.agreement_accepted_at and not self._is_agreement_flow(event):
                await self._send_agreement_hint(event)
                return None
        return await handler(event, data)

    def _is_agreement_flow(self, event: TelegramObject) -> bool:
        if isinstance(event, types.Message):
            return bool(event.text and event.text.startswith("/start"))
        if isinstance(event, types.CallbackQuery):
            return bool(event.data and event.data.startswith("agreement:"))
        return False

    async def _send_agreement_hint(self, event: TelegramObject) -> None:
        if isinstance(event, types.Message):
            await event.answer("Нужно принять соглашение. Нажми /start, чтобы продолжить.")
        elif isinstance(event, types.CallbackQuery):
            await event.answer("Нужно принять соглашение. Нажми /start.", show_alert=True)
