"""Consumidor de eventos del parser: estado del roster, eventos del bus,
notificaciones."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.events import EventBus
from app.services.logparser import ParsedEvent, PlayerEvent
from app.services.notifier import Notifier

log = logging.getLogger(__name__)


@dataclass
class PlayerInfo:
    steam_id: str = ""
    name: str = ""
    world: str = ""
    joined_at: int = 0
    status: str = "offline"


@dataclass
class Roster:
    players: dict[str, PlayerInfo] = field(default_factory=dict)
    by_name: dict[str, str] = field(default_factory=dict)
    last_join_code: str = ""
    last_join_code_server: str = ""
    version: str = ""
    seed: str = ""
    ready: bool = False
    last_world_save: int = 0

    def list_online(self) -> list[PlayerInfo]:
        return [p for p in self.players.values() if p.status == "online"]

    def snapshot(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "version": self.version,
            "seed": self.seed,
            "join_code": self.last_join_code,
            "join_code_server": self.last_join_code_server,
            "online": [p.__dict__ for p in self.list_online()],
            "count": len(self.list_online()),
        }


class PlayerEventHandler:
    def __init__(self, bus: EventBus, notifier: Notifier) -> None:
        self.bus = bus
        self.notifier = notifier
        self.roster = Roster()
        self._handshake: dict[str, int] = {}

    async def feed(self, event: ParsedEvent) -> None:
        ev = event.event
        data = event.data
        if ev == PlayerEvent.READY:
            self.roster.ready = True
        elif ev == PlayerEvent.WORLD_SAVE:
            self.roster.last_world_save = event.ts
        elif ev == PlayerEvent.STEAM_HANDSHAKE:
            sid = data.get("steam_id", "")
            if sid:
                self._handshake[sid] = event.ts
                await self._emit_player(sid, name="", event="connect")
        elif ev == PlayerEvent.PLAYER_CONNECT:
            sid = data.get("steam_id", "")
            if sid:
                self._handshake[sid] = event.ts
        elif ev == PlayerEvent.JOIN:
            name = data.get("name", "")
            sid = self._match_handshake(name)
            if not sid:
                return
            info = self.roster.players.setdefault(sid, PlayerInfo(steam_id=sid))
            info.name = name
            info.status = "online"
            info.joined_at = event.ts
            self.roster.by_name[name] = sid
            await self._emit_player(sid, name=name, event="join")
        elif ev == PlayerEvent.DEATH:
            name = data.get("name", "")
            sid = self.roster.by_name.get(name, "")
            if sid:
                await self._emit_player(sid, name=name, event="death")
        elif ev == PlayerEvent.LEAVE:
            sid, _ = self._oldest_online_without()
            if sid:
                info = self.roster.players.get(sid)
                if info:
                    info.status = "offline"
                await self._emit_player(sid, name=info.name if info else "", event="leave")
        elif ev == PlayerEvent.BAD_PASS:
            sid = data.get("steam_id", "")
            await self.bus.publish("alert", {"kind": "badpass",
                                              "steam_id": sid, "ts": event.ts})
            await self.notifier.event("badpass", {"steam_id": sid[-4:] if sid else "?"})
        elif ev == PlayerEvent.LOGIN_FAIL:
            sid = data.get("steam_id", "")
            await self.bus.publish("alert", {"kind": "badpass",
                                              "steam_id": sid, "ts": event.ts})
        elif ev == PlayerEvent.JOIN_CODE:
            self.roster.last_join_code = data.get("join_code", "")
            self.roster.last_join_code_server = data.get("server_name", "")
            await self.bus.publish("join_code", self.roster.last_join_code)
        elif ev == PlayerEvent.VERSION:
            if "version" in data:
                self.roster.version = data["version"]
            if "seed" in data:
                self.roster.seed = data["seed"]
        await self.bus.publish("roster", self.roster.snapshot())
        await self.bus.publish("log", {"ts": event.ts, "line": event.raw})

    def _match_handshake(self, name: str) -> str:
        candidates = [s for s in self._handshake
                      if s in self.roster.players
                      and self.roster.players[s].status != "online"
                      and not self.roster.players[s].name]
        if candidates:
            return min(candidates, key=lambda s: self._handshake.get(s, 0))
        online = [s for s, p in self.roster.players.items() if p.status == "online"]
        if not online:
            return ""
        return min(online, key=lambda s: self.roster.players[s].joined_at)

    def _oldest_online_without(self) -> tuple[str, int]:
        online = [(s, p) for s, p in self.roster.players.items() if p.status == "online"]
        if not online:
            return "", 0
        online.sort(key=lambda x: x[1].joined_at)
        return online[0][0], online[0][1].joined_at

    async def _emit_player(self, sid: str, name: str, event: str) -> None:
        if not sid:
            return
        info = self.roster.players.setdefault(sid, PlayerInfo(steam_id=sid))
        if name and not info.name:
            info.name = name
        await self.bus.publish("player", {
            "steam_id": sid, "name": info.name or name or sid[-4:],
            "event": event, "ts": int(time.time()),
        })
        if event in {"join", "leave", "death"}:
            await self.notifier.event(event, {
                "name": info.name or name or sid[-4:],
            })

    def snapshot(self) -> dict[str, Any]:
        return self.roster.snapshot()
