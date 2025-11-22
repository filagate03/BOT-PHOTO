from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Face:
    id: int
    user_id: int
    title: str | None
    file_id: str | None
    file_path: str | None
    created_at: datetime
