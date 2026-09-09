"""Scheduler de reinicios, idle-shutdown, chequeo de updates."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import Settings
from app.core.events import EventBus
from app.services.backups import BackupService
from app.services.metrics import MetricsService
from app.services.notifier import Notifier
from app.services.process import ProcessService, ServerState
from app.services.updates import UpdateService

log = logging.getLogger(__name__)


class SchedulerService:
    def __init__(
        self,
        settings: Settings,
        bus: EventBus,
        process: ProcessService,
        backups: BackupService,
        updates: UpdateService,
        metrics: MetricsService,
        notifier: Notifier,
    ) -> None:
        self.settings = settings
        self.bus = bus
        self.process = process
        self.backups = backups
        self.updates = updates
        self.metrics = metrics
        self.notifier = notifier
        self.sched = AsyncIOScheduler(timezone="UTC")
        self._last_idle_check: float = 0.0
        self._last_idle_players: int = 0
        self._idle_since: float | None = None

    async def start(self) -> None:
        if self.settings.schedule.restart_cron:
            try:
                trig = CronTrigger.from_crontab(self.settings.schedule.restart_cron)
                self.sched.add_job(self._scheduled_restart, trigger=trig,
                                   name="scheduled_restart")
            except Exception:
                log.exception("cron inválido: %s", self.settings.schedule.restart_cron)
        self.sched.add_job(self._update_check, IntervalTrigger(hours=6),
                           name="update_check", next_run_time=datetime.utcnow())
        self.sched.add_job(self._idle_check, IntervalTrigger(minutes=1),
                           name="idle_check")
        self.sched.add_job(self._prune_db, IntervalTrigger(hours=12),
                           name="prune_db")
        self.sched.start()
        log.info("Scheduler activo")

    async def stop(self) -> None:
        if self.sched.running:
            self.sched.shutdown(wait=False)

    async def _scheduled_restart(self) -> None:
        for minutes in self.settings.schedule.maintenance_warnings:
            self.sched.add_job(
                self._warn_restart, "date",
                run_date=datetime.utcnow().replace(microsecond=0) + _delta(minutes),
                args=[minutes],
                name=f"warn_{minutes}",
            )
        await self.notifier.event("maintenance", {
            "minutes": 0, "reason": "reinicio programado",
        })
        await self.process.restart(reason="cron", countdown_seconds=0)

    async def _warn_restart(self, minutes: int) -> None:
        await self.notifier.event("maintenance", {
            "minutes": minutes, "reason": "reinicio programado",
        })

    async def _update_check(self) -> None:
        try:
            info = await self.updates.check()
            if info.get("up_to_date") == "no":
                await self.notifier.event("update_available", {
                    "version": info.get("installed", "?"),
                })
        except Exception:
            log.exception("update check falló")

    async def _idle_check(self) -> None:
        if self.settings.schedule.idle_shutdown_minutes <= 0:
            return
        roster = self.metrics.latest()
        players = int(roster.get("players", 0))
        if players == 0:
            if self._idle_since is None:
                self._idle_since = time.time()
            elapsed = (time.time() - self._idle_since) / 60
            if elapsed >= self.settings.schedule.idle_shutdown_minutes:
                state = await self.process.status()
                if state in (ServerState.RUNNING, ServerState.STARTING):
                    await self.process.stop(reason="idle", graceful=True)
                    self._idle_since = None
        else:
            self._idle_since = None

    async def _prune_db(self) -> None:
        try:
            await self.metrics.db.prune(self.settings.metrics.retention_days)
        except Exception:
            log.exception("prune db falló")


def _delta(minutes: int):
    from datetime import timedelta
    return timedelta(minutes=minutes)
