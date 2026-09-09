"""Capa de persistencia con SQLite + aiosqlite."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_samples (
    ts INTEGER NOT NULL,
    cpu REAL, rss REAL, players INTEGER,
    sys_cpu REAL, sys_mem REAL, sys_load REAL,
    net_in REAL, net_out REAL, disk_pct REAL
);
CREATE INDEX IF NOT EXISTS idx_metric_samples_ts ON metric_samples(ts);

CREATE TABLE IF NOT EXISTS metric_5m (
    ts INTEGER NOT NULL,
    cpu REAL, rss REAL, players REAL,
    sys_cpu REAL, sys_mem REAL, sys_load REAL,
    net_in REAL, net_out REAL, disk_pct REAL
);
CREATE TABLE IF NOT EXISTS metric_1h (
    ts INTEGER NOT NULL,
    cpu REAL, rss REAL, players REAL,
    sys_cpu REAL, sys_mem REAL, sys_load REAL,
    net_in REAL, net_out REAL, disk_pct REAL
);

CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    platform TEXT,
    name TEXT,
    first_seen INTEGER,
    last_seen INTEGER,
    last_world TEXT,
    total_seconds INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS player_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    world TEXT,
    joined INTEGER,
    left INTEGER,
    duration INTEGER
);
CREATE INDEX IF NOT EXISTS idx_player_sessions_player ON player_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_sessions_joined ON player_sessions(joined);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,
    reason TEXT,
    path TEXT,
    size INTEGER,
    sha256 TEXT,
    worlds TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,
    actor TEXT,
    action TEXT,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);

CREATE TABLE IF NOT EXISTS alert_state (
    key TEXT PRIMARY KEY,
    state TEXT,
    last_sent INTEGER,
    value REAL
);

CREATE TABLE IF NOT EXISTS server_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path, isolation_level=None)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.executescript(SCHEMA)
        log.info("Base de datos lista en %s", self.path)

    async def stop(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def cursor(self) -> Any:
        assert self._conn is not None, "Database not started"
        async with self._conn.cursor() as cur:
            yield cur

    async def execute(self, sql: str, params: tuple = ()) -> None:
        assert self._conn is not None
        await self._conn.execute(sql, params)

    async def executemany(self, sql: str, params: list[tuple]) -> None:
        assert self._conn is not None
        await self._conn.executemany(sql, params)

    async def fetchone(self, sql: str, params: tuple = ()) -> tuple | None:
        assert self._conn is not None
        async with self._conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        assert self._conn is not None
        async with self._conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def prune(self, days: int) -> int:
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        async with self.cursor() as cur:
            await cur.execute("DELETE FROM metric_samples WHERE ts < ?", (cutoff,))
            await cur.execute("DELETE FROM metric_5m WHERE ts < ?", (cutoff,))
            await cur.execute("DELETE FROM metric_1h WHERE ts < ?", (cutoff,))
            await cur.execute("DELETE FROM audit_log WHERE ts < ?", (cutoff,))
            await cur.execute("DELETE FROM player_sessions WHERE joined < ?", (cutoff,))
            return cur.rowcount
