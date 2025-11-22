from __future__ import annotations

from ..repositories.usage import UsageRepository


class RateLimitService:
    def __init__(self, usage_repo: UsageRepository, default_limit: int) -> None:
        self._usage_repo = usage_repo
        self._default_limit = default_limit

    async def check_limit(self, user_id: int, kind: str, limit: int | None = None) -> bool:
        """
        Returns True when generation is allowed. Any value <= 0 means no cap.
        """
        limit_value = limit if limit is not None else self._default_limit
        if limit_value is None or limit_value <= 0:
            return True
        used = await self._usage_repo.count_recent(user_id, kind, window_minutes=60)
        return used < limit_value

    async def track(self, user_id: int, kind: str) -> None:
        await self._usage_repo.add_event(user_id, kind)


__all__ = ["RateLimitService"]
