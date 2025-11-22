from __future__ import annotations

from ..repositories.users import UserRepository


class TokenService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def balance(self, user_id: int) -> int:
        user = await self._users.get_by_id(user_id)
        return user.tokens if user else 0

    async def ensure_can_spend(self, user_id: int, amount: int) -> bool:
        user = await self._users.get_by_id(user_id)
        return bool(user and user.tokens >= amount)

    async def spend(self, user_id: int, amount: int) -> int:
        """Subtract amount and return new balance (clamped at zero)."""
        return await self._users.update_tokens(user_id, -amount)

    async def add(self, user_id: int, amount: int) -> int:
        """Add amount and return new balance."""
        return await self._users.update_tokens(user_id, amount)


__all__ = ["TokenService"]