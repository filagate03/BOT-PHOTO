from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class Example:
    style: str
    title: str
    caption: str
    file_path: Path


class ExamplesService:
    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._manifest_path = directory / "manifest.json"
        self._examples: dict[str, Example] = {}

    def load(self) -> None:
        if not self._manifest_path.exists():
            self._examples = {}
            return
        with self._manifest_path.open("r", encoding="utf-8") as file:
            items = json.load(file)
        result: dict[str, Example] = {}
        for item in items:
            style = item["style"]
            file_name = item["file"]
            example = Example(
                style=style,
                title=item.get("title", style.title()),
                caption=item.get("caption", ""),
                file_path=self._directory / file_name,
            )
            result[style] = example
        self._examples = result

    def list_examples(self) -> Iterable[Example]:
        return self._examples.values()

    def get_by_style(self, style: str) -> Example | None:
        return self._examples.get(style)


__all__ = ["ExamplesService", "Example"]
