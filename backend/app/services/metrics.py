"""Muestreo de métricas del sistema y del proceso, con persistencia y
downsample."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import psutil

from app.core.config import Settings
from app.core.db import Database
from app.core.events import EventBus
from app.services.notifier import Notifier
from app.services.process import ProcessService, ServerState

log = logging.getLogger(__name__)


class MetricsService:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        process: ProcessService,
        notifier: Notifier,
        bus: EventBus,
    ) -> None:
        self.settings = settings
        self.db = db
        self.process = process
        self.notifier = notifier
        self.bus = bus
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._buffer: deque[dict[str, Any]] = deque(maxlen=600)
        self._last_write = 0.0
        self._last_alert_sent: dict[str, float] = {}
        self._cpu_high_since: float | None = None
        self._state_history: deque[tuple[float, ServerState]] = deque(maxlen=600)
        self._crash_count: list[float] = []
        self._was_running = False
        self._last_psutil = psutil.net_io_counters()
        self._proc_cache: dict[int, psutil.Process] = {}

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="metrics")
        self._downsample_task = asyncio.create_task(self._downsample_loop(), name="downsample")

    async def stop(self) -> None:
        self._stop.set()
        for t in (self._task, self._downsample_task):
            if t:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass

    def latest(self) -> dict[str, Any]:
        return self._buffer[-1] if self._buffer else {}

    def history(self, minutes: int = 60) -> list[dict[str, Any]]:
        cutoff = time.time() - minutes * 60
        return [b for b in self._buffer if b["ts"] >= cutoff]

    async def _run(self) -> None:
        while not self._stop.is_set():
            sample = self._sample()
            self._buffer.append(sample)
            await self.bus.publish("metrics", sample)
            await self._persist(sample)
            await self._check_alerts(sample)
            await asyncio.sleep(self.settings.metrics.interval_seconds)

    async def _downsample_loop(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(300)
            try:
                await self._downsample()
            except Exception:
                log.exception("downsample error")

    def _sample(self) -> dict[str, Any]:
        cpu_proc = 0.0
        rss = 0.0
        proc = self._find_proc()
        if proc is not None:
            try:
                cpu_proc = proc.cpu_percent(interval=None)
                rss = proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc = None
        net = psutil.net_io_counters()
        net_in = net.bytes_recv - self._last_psutil.bytes_recv
        net_out = net.bytes_sent - self._last_psutil.bytes_sent
        self._last_psutil = net
        du = psutil.disk_usage("/")
        load = psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0
        return {
            "ts": time.time(),
            "cpu": cpu_proc,
            "rss": rss,
            "sys_cpu": psutil.cpu_percent(interval=None),
            "sys_mem": psutil.virtual_memory().percent,
            "sys_load": load,
            "net_in": max(0, net_in),
            "net_out": max(0, net_out),
            "disk_pct": du.percent,
        }

    def _find_proc(self) -> psutil.Process | None:
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (p.info["name"] or "").lower()
                cmd = " ".join(p.info["cmdline"] or []).lower()
                if "valheim_server" in name or "valheim_server" in cmd:
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    async def _persist(self, sample: dict[str, Any]) -> None:
        try:
            await self.db.execute(
                "INSERT INTO metric_samples "
                "(ts, cpu, rss, sys_cpu, sys_mem, sys_load, net_in, net_out, disk_pct) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(sample["ts"]), sample["cpu"], sample["rss"],
                    sample["sys_cpu"], sample["sys_mem"], sample["sys_load"],
                    sample["net_in"], sample["net_out"], sample["disk_pct"],
                ),
            )
        except Exception:
            log.exception("metrics persist error")

    async def _downsample(self) -> None:
        cutoff = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
        async with self.db.cursor() as cur:
            await cur.execute(
                "SELECT ts, AVG(cpu), AVG(rss), AVG(sys_cpu), AVG(sys_mem), "
                "AVG(sys_load), AVG(net_in), AVG(net_out), AVG(disk_pct) "
                "FROM metric_samples WHERE ts >= ? AND ts % 60 = 0 "
                "GROUP BY ts / 300", (cutoff,),
            )
            rows = await cur.fetchall()
        if not rows:
            return
        await self.db.executemany(
            "INSERT OR REPLACE INTO metric_5m "
            "(ts, cpu, rss, sys_cpu, sys_mem, sys_load, net_in, net_out, disk_pct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows,
        )

    async def _check_alerts(self, sample: dict[str, Any]) -> None:
        state = await self.process.status()
        self._state_history.append((time.time(), state))
        if state in (ServerState.STOPPED, ServerState.CRASHED):
            await self._alert("down", True, str(state.value))
            self._was_running = False
            self._crash_count = []
        else:
            self._was_running = True
            await self._alert("down", False, "")
            if self._detected_crash_loop():
                await self.notifier.event("crash", {
                    "count": len(self._crash_count),
                    "minutes": self.settings.metrics.crash_loop_window_minutes,
                })
        cpu = sample["sys_cpu"]
        thr = self.settings.metrics.cpu_alert_percent
        if cpu >= thr:
            if self._cpu_high_since is None:
                self._cpu_high_since = time.time()
            elapsed = (time.time() - self._cpu_high_since) / 60
            if elapsed >= self.settings.metrics.cpu_alert_window_minutes:
                await self.notifier.event("resources", {
                    "kind": "CPU", "value": cpu, "threshold": thr,
                })
        else:
            self._cpu_high_since = None
        ram = sample["sys_mem"]
        if ram >= self.settings.metrics.ram_alert_percent:
            await self.notifier.event("resources", {
                "kind": "RAM", "value": ram,
                "threshold": self.settings.metrics.ram_alert_percent,
            })
        disk = sample["disk_pct"]
        if disk >= self.settings.metrics.disk_alert_critical_percent:
            await self.notifier.event("resources", {
                "kind": "Disco", "value": disk,
                "threshold": self.settings.metrics.disk_alert_critical_percent,
            })
        elif disk >= self.settings.metrics.disk_alert_percent:
            await self.notifier.event("resources", {
                "kind": "Disco", "value": disk,
                "threshold": self.settings.metrics.disk_alert_percent,
            })

    async def _alert(self, key: str, active: bool, msg: str) -> None:
        state = self._alert_state.get(key, "ok")
        if active and state != "active":
            self._alert_state[key] = "active"
            await self.notifier.event("down", {"error": msg})
        elif not active and state == "active":
            self._alert_state[key] = "ok"
            await self.notifier.event("up", {"version": ""})

    def _detected_crash_loop(self) -> bool:
        now = time.time()
        window = self.settings.metrics.crash_loop_window_minutes * 60
        recent = [t for t, s in self._state_history
                  if s in (ServerState.STOPPED, ServerState.CRASHED)
                  and now - t < window]
        return len(recent) >= self.settings.metrics.crash_loop_threshold
