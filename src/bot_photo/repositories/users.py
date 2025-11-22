from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import User
from .base import BaseRepository


class UserRepository(BaseRepository):
    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        is_admin: bool,
        starting_tokens: int,
        hourly_limit: int,
    ) -> User:
        await self.db.execute(
            """
            INSERT INTO users(telegram_id, username, full_name, tokens, is_admin, hourly_limit)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                is_admin=excluded.is_admin,
                last_seen_at=CURRENT_TIMESTAMP,
                tokens=CASE WHEN users.tokens = 0 THEN excluded.tokens ELSE users.tokens END
            """,
            (
                telegram_id,
                username,
                full_name,
                starting_tokens,
                1 if is_admin else 0,
                hourly_limit,
            ),
        )
        user = await self.get_by_id(telegram_id)
        if user:
            return user
        raise RuntimeError("Failed to create user")

    async def get_by_id(self, telegram_id: int) -> User | None:
        row = await self.db.fetchone("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        return self._row_to_user(row) if row else None

    async def update_tokens(self, telegram_id: int, delta: int) -> int:
        # Clamp to non-negative and return the new balance.
        row = await self.db.fetchone(
            """
            UPDATE users
            SET tokens = MAX(tokens + ?, 0),
                last_seen_at = CURRENT_TIMESTAMP
            WHERE telegram_id=?
            RETURNING tokens
            """,
            (delta, telegram_id),
        )
        if not row:
            return 0
        return row["tokens"]

    async def set_demo_viewed(self, telegram_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET demo_viewed_at=CURRENT_TIMESTAMP WHERE telegram_id=?",
            (telegram_id,),
        )

    async def record_last_seen(self, telegram_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET last_seen_at=CURRENT_TIMESTAMP WHERE telegram_id=?",
            (telegram_id,),
        )

    async def set_blocked(self, telegram_id: int, blocked: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_blocked=? WHERE telegram_id=?", (1 if blocked else 0, telegram_id)
        )

    async def set_agreement_accepted(self, telegram_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET agreement_accepted_at=CURRENT_TIMESTAMP WHERE telegram_id=?",
            (telegram_id,),
        )

    async def set_admin_status(self, telegram_id: int, is_admin: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_admin=? WHERE telegram_id=?", (1 if is_admin else 0, telegram_id)
        )
    
    async def get_all_users(self) -> list[User]:
        rows = await self.db.fetchall("SELECT * FROM users")
        return [self._row_to_user(row) for row in rows]

    def _row_to_user(self, row: dict[str, Any]) -> User:
        return User(
            telegram_id=row["telegram_id"],
            username=row.get("username"),
            full_name=row.get("full_name"),
            tokens=row.get("tokens", 0),
            is_admin=bool(row.get("is_admin", 0)),
            is_blocked=bool(row.get("is_blocked", 0)),
            hourly_limit=row.get("hourly_limit", 5),
            last_seen_at=self._parse_datetime(row.get("last_seen_at")),
            agreement_accepted_at=self._parse_datetime(row.get("agreement_accepted_at")),
            demo_viewed_at=self._parse_datetime(row.get("demo_viewed_at")),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


__all__ = ["UserRepository"]