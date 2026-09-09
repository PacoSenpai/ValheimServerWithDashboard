"""Control del servicio ``valheim-server`` vía systemd.

El panel solo invoca un conjunto cerrado de acciones, todas vía sudoers
reducido. La parada se hace con ``SIGINT`` (guarda el mundo) y ``TimeoutStopSec``
alcanzable; ``SIGKILL`` es el último recurso.
"""

from __future__ import annotations

import asyncio
import enum
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.services.audit import AuditService

log = logging.getLogger(__name__)


class ServerState(str, enum.Enum):
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"


class ProcessService:
    ALLOWED = {
        "status": "systemctl is-active {svc}",
        "start": "systemctl start {svc}",
        "stop": "systemctl stop {svc}",
        "restart": "systemctl restart {svc}",
        "kill-sigint": "systemctl kill -s SIGINT {svc}",
        "daemon-reload": "systemctl daemon-reload",
    }

    def __init__(self, settings: Settings, audit: AuditService) -> None:
        self.settings = settings
        self.audit = audit
        self.svc = settings.game.service_name
        self._state = ServerState.UNKNOWN
        self._last_change: str = ""
        self._restart_in_progress = False

    @property
    def state(self) -> ServerState:
        return self._state

    async def status(self) -> ServerState:
        code, out = await self._sudo("status")
        if code == 0 and "active" in out and "running" in out:
            self._state = ServerState.RUNNING
        elif code == 0 and "activating" in out:
            self._state = ServerState.STARTING
        elif code == 0 and "deactivating" in out:
            self._state = ServerState.STOPPING
        elif code in (3, 4):
            self._state = ServerState.STOPPED
        else:
            self._state = ServerState.UNKNOWN
        return self._state

    async def start(self, reason: str = "manual") -> ServerState:
        await self.audit.log("server.start", {"reason": reason})
        await self._sudo("start")
        return await self.status()

    async def stop(self, reason: str = "manual", graceful: bool = True) -> ServerState:
        await self.audit.log("server.stop", {"reason": reason, "graceful": graceful})
        if graceful:
            await self._sudo("kill-sigint")
            for _ in range(24):
                await asyncio.sleep(2)
                state = await self.status()
                if state == ServerState.STOPPED:
                    return state
            await self._sudo("stop")
        else:
            await self._sudo("stop")
        return await self.status()

    async def restart(self, reason: str = "manual", graceful: bool = True,
                      countdown_seconds: int = 0) -> ServerState:
        await self.audit.log("server.restart", {
            "reason": reason, "graceful": graceful,
            "countdown": countdown_seconds,
        })
        if countdown_seconds > 0:
            await asyncio.sleep(countdown_seconds)
        await self.stop(reason=reason, graceful=graceful)
        await self._sudo("start")
        return await self.status()

    async def reload_unit(self) -> None:
        await self._sudo("daemon-reload")

    async def _sudo(self, action: str) -> tuple[int, str]:
        template = self.ALLOWED[action]
        cmd = template.format(svc=self.svc)
        full = ["sudo", "--non-interactive", "sh", "-c", cmd]
        log.info("sudo %s", cmd)
        try:
            proc = await asyncio.create_subprocess_exec(
                *full,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        except TimeoutError:
            log.error("Timeout en %s", cmd)
            return 124, ""
        out = (stdout or b"").decode("utf-8", errors="replace").strip()
        err = (stderr or b"").decode("utf-8", errors="replace").strip()
        if err:
            log.warning("stderr: %s", err)
        if action == "status":
            self._last_change = datetime.now(UTC).isoformat(timespec="seconds")
        return proc.returncode or 0, out + ("\n" + err if err else "")

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "updated_at": self._last_change,
        }
