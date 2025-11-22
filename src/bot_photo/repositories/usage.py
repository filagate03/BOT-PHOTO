from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseRepository


class UsageRepository(BaseRepository):
    async def add_event(self, user_id: int, kind: str) -> None:
        await self.db.execute(
            "INSERT INTO usage_events(user_id, kind) VALUES(?, ?)", (user_id, kind)
        )

    async def count_recent(self, user_id: int, kind: str, window_minutes: int) -> int:
        threshold = datetime.utcnow() - timedelta(minutes=window_minutes)
        formatted = threshold.strftime("%Y-%m-%d %H:%M:%S")
        value = await self.db.fetchval(
            """
            SELECT COUNT(*) FROM usage_events
            WHERE user_id=? AND kind=? AND created_at >= ?
            """,
            (user_id, kind, formatted),
        )
        return int(value or 0)


__all__ = ["UsageRepository"]
