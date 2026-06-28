from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class JsonStateStorage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._read()
            return data.get(user_id)

    def save_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            data[user_id] = user_data
            self._write(data)
