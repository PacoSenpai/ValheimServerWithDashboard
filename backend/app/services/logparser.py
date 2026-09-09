"""Parser de líneas de log de Valheim.

Reglas versionadas en ``RULES`` (orden importa: la primera que hace match
prevalece). Los nombres siguen el ``PlayerEvent`` cuando aplique, para que el
handler los consuma directamente.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class PlayerEvent:
    READY = "ready"
    JOIN = "join"
    LEAVE = "leave"
    DEATH = "death"
    BAD_PASS = "bad_password"
    WORLD_SAVE = "world_save"
    PLAYER_CONNECT = "player_connect"
    STEAM_HANDSHAKE = "steam_handshake"
    JOIN_CODE = "join_code"
    VERSION = "version"
    LOGIN_FAIL = "login_fail"
    NETWORK_WARN = "network_warn"
    UNKNOWN = "unknown"


@dataclass
class Rule:
    name: str
    regex: re.Pattern[str]
    event: str
    fields: list[str] = field(default_factory=list)


def _rx(pat: str) -> re.Pattern[str]:
    return re.compile(pat)


RULES: list[Rule] = [
    Rule("ready_dungeon", _rx(r"DungeonDB Start"), PlayerEvent.READY),
    Rule("ready_game", _rx(r"Game server connected"), PlayerEvent.READY),
    Rule("world_save", _rx(r"World saved"), PlayerEvent.WORLD_SAVE),
    Rule(
        "handshake", _rx(r"Got handshake from client (\d+)"),
        PlayerEvent.STEAM_HANDSHAKE, ["steam_id"],
    ),
    Rule(
        "got_connection", _rx(r"Got connection SteamID (\d+)"),
        PlayerEvent.PLAYER_CONNECT, ["steam_id"],
    ),
    Rule(
        "death",
        _rx(r"Got character ZDOID from ([^\s:]+)\s*:\s*([\w-]+):0:0(?=\s|$)"),
        PlayerEvent.DEATH, ["name", "zdoid"],
    ),
    Rule(
        "character",
        _rx(r"Got character ZDOID from ([^\s:]+)\s*:\s*([\w-]+):\d+"),
        PlayerEvent.JOIN, ["name", "zdoid"],
    ),
    Rule(
        "closing_socket", _rx(r"Closing socket (\d+)"),
        PlayerEvent.LEAVE, ["socket"],
    ),
    Rule(
        "bad_password", _rx(r"Peer (\d+) has wrong password"),
        PlayerEvent.BAD_PASS, ["steam_id"],
    ),
    Rule(
        "auth_fail",
        _rx(r"Failed to authenticate user (\d+),?\s*password mismatch"),
        PlayerEvent.LOGIN_FAIL, ["steam_id"],
    ),
    Rule(
        "join_code_v1",
        _rx(r'New session server "([^"]+)" that has join code (\w{4,8})'),
        PlayerEvent.JOIN_CODE, ["server_name", "join_code"],
    ),
    Rule(
        "join_code_v2",
        _rx(r'Session "([^"]+)" with join code (\w{4,8})'),
        PlayerEvent.JOIN_CODE, ["server_name", "join_code"],
    ),
    Rule(
        "version", _rx(r"Game version:\s*([\w.\-]+)"),
        PlayerEvent.VERSION, ["version"],
    ),
    Rule(
        "world_seed", _rx(r"World: \S+ \(seed=([\w-]+)\)"),
        PlayerEvent.VERSION, ["seed"],
    ),
    Rule(
        "network_warn",
        _rx(r"Steam: warning network congestion"),
        PlayerEvent.NETWORK_WARN,
    ),
]


@dataclass
class ParsedEvent:
    rule: str
    event: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: int = field(default_factory=lambda: int(time.time()))
    raw: str = ""


_TS_RE = re.compile(r"^(\d+/\d+/\d+ \d+:\d+:\d+):\s*")


def parse_line(line: str) -> ParsedEvent | None:
    line = line.rstrip("\r\n")
    if not line:
        return None
    ts = int(time.time())
    m = _TS_RE.match(line)
    if m:
        try:
            ts = int(
                datetime.strptime(m.group(1), "%m/%d/%Y %H:%M:%S")
                .replace(tzinfo=UTC)
                .timestamp()
            )
        except ValueError:
            pass
        body = line[m.end():]
    else:
        body = line
    for rule in RULES:
        m = rule.regex.search(body)
        if m:
            data: dict[str, Any] = {}
            for i, name in enumerate(rule.fields, start=1):
                try:
                    data[name] = m.group(i)
                except (IndexError, AttributeError):
                    pass
            return ParsedEvent(rule=rule.name, event=rule.event,
                               data=data, ts=ts, raw=line)
    return ParsedEvent(rule="unmatched", event=PlayerEvent.UNKNOWN,
                       data={"body": body}, ts=ts, raw=line)


def parse_lines(lines: Iterable[str]) -> list[ParsedEvent]:
    return [e for e in (parse_line(line) for line in lines) if e is not None]
