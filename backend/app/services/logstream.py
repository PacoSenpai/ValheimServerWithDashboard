"""Tail del fichero de log y broadcast a un handler."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class LogStream:
    BUFFER_SIZE = 5000

    def __init__(self, path: Path) -> None:
        self.path = path
        self.buffer: deque[str] = deque(maxlen=self.BUFFER_SIZE)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._handler: Callable[[Any], Any] | None = None
        self._pos = 0
        self._inode: int = 0

    def start(self, handler: Any) -> None:
        self._handler = handler
        self._stop.clear()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="logstream")

    def stop(self) -> None:
        self._stop.set()

    async def _run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        last_size = self.path.stat().st_size if self.path.exists() else 0
        with self.path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(last_size)
            while not self._stop.is_set():
                line = fh.readline()
                if line:
                    self.buffer.append(line.rstrip("\n"))
                    if self._handler is not None:
                        try:
                            from app.services.logparser import parse_line
                            ev = parse_line(line)
                            if ev is not None:
                                result = self._handler.feed(ev)
                                if asyncio.iscoroutine(result):
                                    await result
                        except Exception:
                            log.exception("Error alimentando el parser")
                    continue
                await asyncio.sleep(0.5)

    def recent(self, limit: int = 200) -> list[str]:
        if limit <= 0:
            return []
        return list(self.buffer)[-limit:]
