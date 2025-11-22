from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PromptGeneration:
    id: int
    user_id: int
    template: str | None
    prompt: str
    status: str
    result_path: str | None
    result_file_id: str | None
    tokens_spent: int | None
    created_at: datetime
