from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    telegram_id: int
    username: str | None
    full_name: str | None
    tokens: int
    is_admin: bool
    is_blocked: bool
    hourly_limit: int
    last_seen_at: datetime | None
    agreement_accepted_at: datetime | None
    demo_viewed_at: datetime | None
