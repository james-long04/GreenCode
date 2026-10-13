"""In-memory ring buffer of recent log records, so the admin panel can show what the
server has been doing without anyone tailing a terminal."""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

_BUFFER: deque[dict[str, Any]] = deque(maxlen=500)
_LOCK = threading.Lock()


class RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            }
        except Exception:  # noqa: BLE001
            return
        with _LOCK:
            _BUFFER.append(entry)


def install() -> None:
    root = logging.getLogger()
    if any(isinstance(h, RingBufferHandler) for h in root.handlers):
        return
    handler = RingBufferHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)


def recent(limit: int = 200, level: str | None = None) -> list[dict[str, Any]]:
    threshold = logging.getLevelName(level.upper()) if level else logging.NOTSET
    if not isinstance(threshold, int):
        threshold = logging.NOTSET
    with _LOCK:
        rows = list(_BUFFER)
    rows = [r for r in rows if logging.getLevelName(r["level"]) >= threshold]
    return rows[-limit:]
