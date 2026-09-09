"""Registro de auditoría en SQLite."""

from __future__ import annotations

import json
import time

from app.core.db import Database


class AuditService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def log(self, action: str, payload: dict) -> None:
        await self.db.execute(
            "INSERT INTO audit_log (ts, actor, action, payload) VALUES (?, ?, ?, ?)",
            (int(time.time()), "admin", action, json.dumps(payload, ensure_ascii=False)),
        )

    async def list(self, limit: int = 200) -> list[dict]:
        rows = await self.db.fetchall(
            "SELECT id, ts, actor, action, payload FROM audit_log "
            "ORDER BY ts DESC LIMIT ?", (limit,),
        )
        out: list[dict] = []
        for r in rows:
            try:
                payload = json.loads(r[4] or "{}")
            except json.JSONDecodeError:
                payload = {}
            out.append({"id": r[0], "ts": r[1], "actor": r[2],
                        "action": r[3], "payload": payload})
        return out
