from __future__ import annotations

from ..db import Database


class BaseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def db(self) -> Database:
        return self._db


__all__ = ["BaseRepository"]
