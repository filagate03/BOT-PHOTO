from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import Face
from .base import BaseRepository


class FaceRepository(BaseRepository):
    async def add_face(
        self, user_id: int, title: str | None, file_id: str | None, file_path: str | None
    ) -> Face:
        await self.db.execute(
            "INSERT INTO faces(user_id, title, file_id, file_path) VALUES(?, ?, ?, ?)",
            (user_id, title, file_id, file_path),
        )
        row = await self.db.fetchone(
            "SELECT * FROM faces WHERE rowid=last_insert_rowid()"
        )
        if not row:
            raise RuntimeError("Failed to insert face")
        return self._row_to_face(row)

    async def list_faces(self, user_id: int, limit: int = 10) -> list[Face]:
        rows = await self.db.fetchall(
            "SELECT * FROM faces WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [self._row_to_face(row) for row in rows]

    async def delete_face(self, face_id: int, user_id: int) -> None:
        await self.db.execute(
            "DELETE FROM faces WHERE id=? AND user_id=?", (face_id, user_id)
        )

    async def update_title(self, face_id: int, user_id: int, title: str | None) -> None:
        await self.db.execute(
            "UPDATE faces SET title=? WHERE id=? AND user_id=?", (title, face_id, user_id)
        )

    async def update_file_path(self, face_id: int, user_id: int, file_path: str) -> None:
        await self.db.execute(
            "UPDATE faces SET file_path=? WHERE id=? AND user_id=?", (file_path, face_id, user_id)
        )

    async def get_by_id(self, face_id: int, user_id: int) -> Face | None:
        row = await self.db.fetchone("SELECT * FROM faces WHERE id=? AND user_id=?", (face_id, user_id))
        return self._row_to_face(row) if row else None

    def _row_to_face(self, row: dict[str, Any]) -> Face:
        return Face(
            id=row["id"],
            user_id=row["user_id"],
            title=row.get("title"),
            file_id=row.get("file_id"),
            file_path=row.get("file_path"),
            created_at=self._parse_datetime(row.get("created_at")),
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        return datetime.fromisoformat(value) if value else datetime.utcnow()


__all__ = ["FaceRepository"]
