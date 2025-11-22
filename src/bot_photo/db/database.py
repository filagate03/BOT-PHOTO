from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Iterable

import aiosqlite


class Database:
    """Small async wrapper around aiosqlite."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._conn:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path.as_posix())
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys=ON;")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not initialized")
        return self._conn

    async def run_script(self, script_path: Path) -> None:
        async with self._lock:
            with script_path.open("r", encoding="utf-8") as file:
                script = file.read()
            await self.connection.executescript(script)
            await self.connection.commit()

    async def execute(self, query: str, params: Iterable[Any] | None = None) -> None:
        async with self._lock:
            await self.connection.execute(query, tuple(params or ()))
            await self.connection.commit()

    async def fetchone(
        self, query: str, params: Iterable[Any] | None = None
    ) -> dict[str, Any] | None:
        async with self.connection.execute(query, tuple(params or ())) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(
        self, query: str, params: Iterable[Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self.connection.execute(query, tuple(params or ())) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def fetchval(
        self, query: str, params: Iterable[Any] | None = None
    ) -> Any | None:
        row = await self.fetchone(query, params)
        if row:
            return next(iter(row.values()))
        return None
