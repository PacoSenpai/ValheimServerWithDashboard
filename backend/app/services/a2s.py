"""Sondeo A2S_INFO/A2S_PLAYERS para estado público (nombre, jugadores)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import a2s

from app.core.config import Settings
from app.core.events import EventBus

log = logging.getLogger(__name__)


class A2SProbe:
    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self.last: dict[str, Any] = {}

    async def start(self) -> None:
        if not self.settings.network.use_a2s:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="a2s")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()

    async def _run(self) -> None:
        addr = ("127.0.0.1", self.settings.game.port + 1)
        while not self._stop.is_set():
            try:
                info = await asyncio.to_thread(a2s.info, addr, timeout=2.0)
                payload = {
                    "name": info.name, "map": info.map_name,
                    "players": info.player_count, "max_players": info.max_players,
                    "version": info.version, "source": "a2s",
                }
                self.last = payload
                await self.bus.publish("a2s", payload)
                try:
                    players = await asyncio.to_thread(a2s.players, addr, timeout=2.0)
                    payload["player_names"] = [p.name for p in players]
                except Exception:
                    pass
            except Exception as exc:
                self.last = {"source": "a2s", "error": str(exc), "players": 0}
                await self.bus.publish("a2s", self.last)
            await asyncio.sleep(self.settings.network.a2s_probe_interval_seconds)
