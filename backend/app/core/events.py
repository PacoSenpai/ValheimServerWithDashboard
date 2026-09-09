"""Bus de eventos in-process para WS y notifier."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

log = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue[Any]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Any) -> None:
        async with self._lock:
            queues = list(self._subs.get(topic, set()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                log.warning("Cola llena para topic %s, descartando", topic)

    async def subscribe(self, topic: str) -> AsyncIterator[Any]:
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=512)
        async with self._lock:
            self._subs[topic].add(q)
        try:
            while True:
                item = await q.get()
                yield item
        finally:
            async with self._lock:
                self._subs[topic].discard(q)
                if not self._subs[topic]:
                    self._subs.pop(topic, None)


bus = EventBus()
