from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import Session
from .base import BaseRepository


class SessionRepository(BaseRepository):
    async def create_session(
        self,
        user_id: int,
        style: str,
        prompt: str | None,
        status: str,
        tokens_spent: int,
    ) -> Session:
        await self.db.execute(
            """
            INSERT INTO sessions(user_id, style, prompt, status, tokens_spent)
            VALUES(?, ?, ?, ?, ?)
            """,
            (user_id, style, prompt, status, tokens_spent),
        )
        row = await self.db.fetchone(
            "SELECT * FROM sessions WHERE rowid=last_insert_rowid()"
        )
        if not row:
            raise RuntimeError("Session create failed")
        return self._row_to_session(row)

    async def update_status(
        self,
        session_id: int,
        status: str,
        result_path: str | None = None,
        result_file_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            UPDATE sessions
            SET status=?, result_path=COALESCE(?, result_path),
                result_file_id=COALESCE(?, result_file_id),
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, result_path, result_file_id, session_id),
        )

    async def list_for_user(self, user_id: int, limit: int = 10) -> list[Session]:
        rows = await self.db.fetchall(
            "SELECT * FROM sessions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [self._row_to_session(row) for row in rows]

    async def get_by_id(self, session_id: int) -> Session | None:
        row = await self.db.fetchone("SELECT * FROM sessions WHERE id=?", (session_id,))
        return self._row_to_session(row) if row else None

    def _row_to_session(self, row: dict[str, Any]) -> Session:
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            style=row["style"],
            prompt=row.get("prompt"),
            status=row["status"],
            result_path=row.get("result_path"),
            result_file_id=row.get("result_file_id"),
            tokens_spent=row.get("tokens_spent"),
            created_at=self._parse_datetime(row.get("created_at")),
            updated_at=self._parse_datetime(row.get("updated_at")),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        return datetime.fromisoformat(value) if value else datetime.utcnow()


__all__ = ["SessionRepository"]
