from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Session:
    id: int
    user_id: int
    style: str
    prompt: str | None
    status: str
    result_path: str | None
    result_file_id: str | None
    tokens_spent: int | None
    created_at: datetime
    updated_at: datetime
