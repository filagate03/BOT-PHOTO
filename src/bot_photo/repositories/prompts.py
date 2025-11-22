from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import PromptGeneration
from .base import BaseRepository


class PromptRepository(BaseRepository):
    async def create(
        self,
        user_id: int,
        prompt: str,
        template: str | None,
        status: str,
        tokens_spent: int,
    ) -> PromptGeneration:
        await self.db.execute(
            """
            INSERT INTO prompt_generations(user_id, prompt, template, status, tokens_spent)
            VALUES(?, ?, ?, ?, ?)
            """,
            (user_id, prompt, template, status, tokens_spent),
        )
        row = await self.db.fetchone(
            "SELECT * FROM prompt_generations WHERE rowid=last_insert_rowid()"
        )
        if not row:
            raise RuntimeError("Prompt record failed")
        return self._row_to_prompt(row)

    async def update_status(
        self,
        record_id: int,
        status: str,
        result_path: str | None = None,
        result_file_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            UPDATE prompt_generations
            SET status=?, result_path=COALESCE(?, result_path),
                result_file_id=COALESCE(?, result_file_id)
            WHERE id=?
            """,
            (status, result_path, result_file_id, record_id),
        )

    async def list_for_user(self, user_id: int, limit: int = 10) -> list[PromptGeneration]:
        rows = await self.db.fetchall(
            """
            SELECT * FROM prompt_generations
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [self._row_to_prompt(row) for row in rows]

    def _row_to_prompt(self, row: dict[str, Any]) -> PromptGeneration:
        return PromptGeneration(
            id=row["id"],
            user_id=row["user_id"],
            template=row.get("template"),
            prompt=row["prompt"],
            status=row["status"],
            result_path=row.get("result_path"),
            result_file_id=row.get("result_file_id"),
            tokens_spent=row.get("tokens_spent"),
            created_at=self._parse_datetime(row.get("created_at")),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        return datetime.fromisoformat(value) if value else datetime.utcnow()


__all__ = ["PromptRepository"]
