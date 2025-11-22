from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


def _default_path(relative: str) -> Path:
    return (ROOT_DIR / relative).expanduser().resolve()


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    nano_banana_api_key: str = Field(..., alias="NANO_BANANA_API_KEY")
    nano_banana_base_url: str = Field("https://api.artemox.com", alias="NANO_BANANA_BASE_URL")
    nano_banana_model: str = Field("gemini-2.5-flash-image-preview", alias="NANO_BANANA_MODEL")
    nano_banana_fallback_model: str | None = Field(
        None, alias="NANO_BANANA_FALLBACK_MODEL"
    )
    database_path: Path = Field(_default_path("var/app.db"), alias="DATABASE_PATH")
    faces_path: Path = Field(_default_path("storage/faces"), alias="FACES_PATH")
    sessions_path: Path = Field(_default_path("storage/sessions"), alias="SESSIONS_PATH")
    examples_path: Path = Field(_default_path("repo/examples"), alias="EXAMPLES_PATH")
    hourly_limit: int = Field(0, alias="HOURLY_LIMIT")
    starting_tokens: int = Field(10, alias="STARTING_TOKENS")
    cost_per_session: int = Field(5, alias="COST_PER_SESSION")
    cost_per_prompt: int = Field(1, alias="COST_PER_PROMPT")
    admin_ids: tuple[int, ...] = Field((742200799,), alias="ADMIN_IDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator(
        "database_path", "faces_path", "sessions_path", "examples_path", mode="before"
    )
    @classmethod
    def expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | int | tuple[int, ...] | list[int]) -> tuple[int, ...]:
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            return tuple(int(part) for part in parts)
        if isinstance(value, (tuple, list)):
            return tuple(int(part) for part in value)
        if isinstance(value, int):
            return (value,)
        if value is None:
            return ()
        raise TypeError("Unsupported admin_ids type")

    @field_validator("nano_banana_fallback_model", mode="before")
    @classmethod
    def parse_optional_model(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


__all__ = ["Settings"]
