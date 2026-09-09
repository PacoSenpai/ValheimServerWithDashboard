"""Snapshots del savedir con ``tar.zst``, retención y restauración."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.audit import AuditService
from app.services.process import ProcessService, ServerState

log = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    id: int
    ts: int
    reason: str
    path: Path
    size: int
    sha256: str
    worlds: list[str]

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "reason": self.reason,
            "filename": self.path.name,
            "size_bytes": self.size,
            "sha256": self.sha256,
            "worlds": self.worlds,
        }


class BackupService:
    def __init__(self, settings: Settings, audit: AuditService) -> None:
        self.settings = settings
        self.audit = audit
        self.dir = settings.game.backups_dir
        self.savedir = settings.game.savedir

    async def list(self) -> list[BackupInfo]:
        rows = await self.audit.db.fetchall(
            "SELECT id, ts, reason, path, size, sha256, worlds "
            "FROM backups ORDER BY ts DESC"
        )
        out: list[BackupInfo] = []
        for r in rows:
            try:
                worlds = (r[6] or "").split(",") if r[6] else []
                out.append(BackupInfo(id=r[0], ts=r[1], reason=r[2],
                                     path=Path(r[3]), size=r[4], sha256=r[5],
                                     worlds=worlds))
            except FileNotFoundError:
                continue
        return out

    async def create(self, reason: str) -> BackupInfo:
        self.dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        fname = f"backup-{ts}-{reason}.tar.zst"
        out = self.dir / fname
        cmd = [
            "tar", "--zstd", "-cf", str(out),
            "-C", str(self.savedir.parent),
            self.savedir.name,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = (stderr or b"").decode("utf-8", "replace")
            await self.audit.log("backup.fail", {"reason": reason, "error": err})
            raise RuntimeError(f"tar falló: {err.strip()}")
        sha = self._sha256(out)
        size = out.stat().st_size
        worlds = sorted(p.name for p in (self.savedir / "worlds_local").iterdir()
                        if p.is_dir()) if (self.savedir / "worlds_local").is_dir() else []
        await self.audit.db.execute(
            "INSERT INTO backups (ts, reason, path, size, sha256, worlds) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, reason, str(out), size, sha, ",".join(worlds)),
        )
        await self.audit.log("backup.ok", {"reason": reason, "size": size, "worlds": worlds})
        await self._enforce_retention()
        bid = (await self.audit.db.fetchone("SELECT last_insert_rowid()"))[0]
        return BackupInfo(id=bid, ts=ts, reason=reason, path=out,
                          size=size, sha256=sha, worlds=worlds)

    async def restore(self, backup_id: int) -> bool:
        rows = await self.audit.db.fetchall(
            "SELECT path FROM backups WHERE id = ?", (backup_id,),
        )
        if not rows:
            return False
        src = Path(rows[0][0])
        if not src.is_file():
            return False
        await self.audit.log("restore.start", {"backup": backup_id})
        safety = await self.create(reason=f"pre-restore-{backup_id}")
        proc = ProcessService(self.settings, self.audit)
        await proc.stop(reason=f"restore:{backup_id}")
        cmd = ["tar", "--zstd", "-xf", str(src), "-C", str(self.savedir.parent)]
        sub = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await sub.communicate()
        if sub.returncode != 0:
            await self.audit.log("restore.fail", {"backup": backup_id,
                                                  "error": (stderr or b"").decode()})
            raise RuntimeError("tar falló en restore")
        await proc.start(reason=f"post-restore:{backup_id}")
        await self.audit.log("restore.ok", {
            "backup": backup_id, "safety": safety.id,
        })
        return True

    async def _enforce_retention(self) -> None:
        rows = await self.audit.db.fetchall(
            "SELECT id, path FROM backups ORDER BY ts DESC"
        )
        keep = self.settings.backup.max_keep
        for row in rows[keep:]:
            try:
                Path(row[1]).unlink(missing_ok=True)
            except OSError:
                pass
            await self.audit.db.execute("DELETE FROM backups WHERE id = ?", (row[0],))

    @staticmethod
    def _sha256(path: Path, chunk: int = 1 << 20) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                b = fh.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
