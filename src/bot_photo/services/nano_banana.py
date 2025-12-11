from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

import aiohttp


class NanoBananaAPIError(RuntimeError):
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.payload = payload
        super().__init__(f"Nano Banana API error {status}: {payload}")

    def is_model_error(self) -> bool:
        if self.status in {400, 401, 403, 404} and isinstance(self.payload, dict):
            detail = str(self.payload.get("detail", "")).lower()
            error = self.payload.get("error") or {}
            message = detail
            if isinstance(error, dict):
                message += str(error.get("message", "")).lower()
            return "model" in message
        return False

    def is_guardrail_model_block(self) -> bool:
        if self.status in {400, 500} and isinstance(self.payload, dict):
            error = self.payload.get("error")
            if isinstance(error, dict):
                message = str(error.get("message", "")).lower()
                if "guardrail" in message and "model" in message:
                    return True
        return False


class NanoBananaClient:
    def __init__(self, api_key: str, base_url: str, model: str, fallback_model: str | None) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._fallback_model = fallback_model
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session and not self._session.closed:
            return self._session
        self._session = aiohttp.ClientSession(headers=self._default_headers())
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate_photosession(
        self,
        style: str,
        prompt: str | None,
        orientation: str,
        face_urls: Iterable[str],
    ) -> dict[str, Any]:
        base_prompt = prompt or f"Высококлассная реалистичная фотосессия в стиле {style}"

        if orientation == "vertical":
            aspect_ratio_prompt = "vertical aspect ratio, 9:16"
        elif orientation == "horizontal":
            aspect_ratio_prompt = "horizontal aspect ratio, 16:9"
        else:
            aspect_ratio_prompt = ""

        if aspect_ratio_prompt:
            base_prompt = f"{aspect_ratio_prompt}, {base_prompt}"

        prompt_text = (
            f"{base_prompt}, 1080p resolution, high-end retouch, natural skin texture, "
            "подбери сцену, свет и композицию под стиль, "
            "выбери одежду и аксессуары, гармоничные с локацией, "
            "определи пол/образ по лицу и подбери соответствующий образ, "
            "premium fashion lighting, cinematic depth of field"
        )

        async def _request(model: str, include_faces: bool) -> dict[str, Any]:
            parts: list[dict[str, Any]] = []
            if include_faces:
                parts.extend(self._inline_face_parts(face_urls))
            parts.append({"text": prompt_text})
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "safetySettings": self._safety_settings(),
            }
            return await self._post(f"/models/{model}:generateContent", payload)

        try:
            return await self._with_fallback(lambda m: _request(m, True))
        except NanoBananaAPIError as exc:
            if exc.is_guardrail_model_block():
                return await self._with_fallback(lambda m: _request(m, False))
            raise

    async def generate_prompt(
        self,
        prompt: str,
        template: str | None = None,
        face_urls: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        text_prompt = f"{template}: {prompt}" if template else prompt

        async def _request(model: str) -> dict[str, Any]:
            parts: list[dict[str, Any]] = []
            if face_urls:
                parts.extend(self._inline_face_parts(face_urls))
            parts.append({"text": text_prompt})
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "safetySettings": self._safety_settings(),
            }
            return await self._post(f"/models/{model}:generateContent", payload)

        return await self._with_fallback(_request)

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"{self._base_url}{endpoint}"
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status >= 400:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = text
                raise NanoBananaAPIError(resp.status, data)
            return await resp.json()

    async def _with_fallback(
        self, request: Callable[[str], Awaitable[dict[str, Any]]]
    ) -> dict[str, Any]:
        models_to_try = [self._model]
        if self._fallback_model and self._fallback_model not in models_to_try:
            models_to_try.append(self._fallback_model)
        last_error: NanoBananaAPIError | None = None
        for model in models_to_try:
            try:
                return await request(model)
            except NanoBananaAPIError as exc:
                if (exc.is_model_error() or exc.is_guardrail_model_block()) and model != models_to_try[-1]:
                    last_error = exc
                    continue
                raise
        if last_error:
            raise last_error

    def _inline_face_parts(self, sources: Iterable[str]) -> Iterable[dict[str, Any]]:
        for source in sources:
            path = Path(source)
            if not path.exists():
                continue
            mime = self._guess_mime_type(path)
            yield {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(path.read_bytes()).decode("utf-8"),
                }
            }

    @staticmethod
    def _guess_mime_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".png":
            return "image/png"
        if suffix == ".webp":
            return "image/webp"
        return "image/jpeg"

    @staticmethod
    def _safety_settings() -> list[dict[str, str]]:
        categories = [
            "HARM_CATEGORY_HATE_SPEECH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "HARM_CATEGORY_DANGEROUS_CONTENT",
            "HARM_CATEGORY_HARASSMENT",
            "HARM_CATEGORY_CIVIC_INTEGRITY",
        ]
        return [{"category": cat, "threshold": "BLOCK_NONE"} for cat in categories]

    def _default_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key.startswith("sk-"):
            headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            headers["x-goog-api-key"] = self._api_key
        return headers


__all__ = ["NanoBananaClient", "NanoBananaAPIError"]
