from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Payment:
    invoice_id: int
    user_id: int
    amount_usdt: float
    tokens: int
    status: str
    invoice_url: str | None = None
    payload: str | None = None
    created_at: datetime | None = None
    paid_at: datetime | None = None
    credited_at: datetime | None = None


__all__ = ["Payment"]
