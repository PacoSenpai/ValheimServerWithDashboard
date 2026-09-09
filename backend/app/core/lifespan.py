"""Inicialización y apagado de servicios de fondo."""

from __future__ import annotations

import logging
import os

import bcrypt

from app.core.config import Settings
from app.core.db import Database
from app.core.events import EventBus
from app.core.registry import Registry
from app.services.a2s import A2SProbe
from app.services.audit import AuditService
from app.services.backups import BackupService
from app.services.lists import ListService
from app.services.logstream import LogStream
from app.services.metrics import MetricsService
from app.services.notifier import Notifier
from app.services.process import ProcessService
from app.services.roster import PlayerEventHandler
from app.services.scheduler import SchedulerService
from app.services.steam import SteamService
from app.services.updates import UpdateService
from app.services.worlds import WorldService

log = logging.getLogger(__name__)


class Lifespan:
    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self.registry: Registry | None = None

    async def startup(self) -> None:
        log.info("Inicializando Valheim Dashboard")
        if not self._first_run_done():
            self._first_run()
        db = Database(self.settings.storage.db_path)
        await db.start()
        audit = AuditService(db)
        worlds = WorldService(self.settings.game.savedir)
        lists = ListService(self.settings.game.savedir)
        steam = SteamService(self.settings)
        process = ProcessService(self.settings, audit)
        backups = BackupService(self.settings, audit)
        updates = UpdateService(self.settings, steam, backups)
        notifier = Notifier(self.settings)
        await notifier.start()
        metrics = MetricsService(self.settings, db, process, notifier, self.bus)
        logstream = LogStream(self.settings.game.log_file)
        parser = PlayerEventHandler(self.bus, notifier)
        a2s = A2SProbe(self.settings, self.bus)
        scheduler = SchedulerService(
            settings=self.settings,
            bus=self.bus,
            process=process,
            backups=backups,
            updates=updates,
            metrics=metrics,
            notifier=notifier,
        )
        await scheduler.start()
        await metrics.start()
        await a2s.start()
        logstream.start(parser)
        self.registry = Registry(
            settings=self.settings, db=db, bus=self.bus, audit=audit,
            process=process, backups=backups, updates=updates,
            metrics=metrics, worlds=worlds, lists=lists,
            logstream=logstream, parser=parser, a2s=a2s,
            scheduler=scheduler, notifier=notifier,
        )
        log.info("Valheim Dashboard listo")

    async def shutdown(self) -> None:
        log.info("Apagando Valheim Dashboard")
        if not self.registry:
            return
        r = self.registry
        await r.scheduler.stop()
        await r.a2s.stop()
        await r.metrics.stop()
        r.logstream.stop()
        await r.notifier.close()
        await r.db.stop()
        log.info("Apagado completo")

    def _first_run_done(self) -> bool:
        return self.settings.panel.secret_key_file.is_file()

    def _first_run(self) -> None:
        log.info("Primera ejecución: generando secretos")
        for path in (
            self.settings.panel.secret_key_file.parent,
            self.settings.storage.data_dir,
            self.settings.game.savedir,
            self.settings.game.backups_dir,
            self.settings.game.log_file.parent,
            self.settings.panel.admin_password_hash_file.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(path, 0o700)
            except PermissionError:
                pass
        secret = os.urandom(48)
        with open(self.settings.panel.secret_key_file, "wb") as fh:
            fh.write(secret)
        os.chmod(self.settings.panel.secret_key_file, 0o600)
        password = os.environ.get("VALHEIM_DASHBOARD_INIT_PASSWORD", "admin")
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        with open(self.settings.panel.admin_password_hash_file, "wb") as fh:
            fh.write(hashed)
        os.chmod(self.settings.panel.admin_password_hash_file, 0o600)
        for fname in ("adminlist.txt", "bannedlist.txt", "permittedlist.txt"):
            target = self.settings.game.savedir / fname
            if not target.is_file():
                target.write_text("")
        self._write_env()
        log.warning(
            "Password inicial del panel: %s  (cámbialo en cuanto puedas desde la UI)",
            password,
        )

    def _write_env(self) -> None:
        from app.services.args import build_argv

        argv = build_argv(self.settings.game, self.settings.modifiers)
        content = (
            "# Generado por valheim-dashboard. Se sobrescribe al aplicar cambios.\n"
            "ARGV=" + " ".join(f'"{a}"' if " " in a else a for a in argv) + "\n"
        )
        self.settings.game.env_file.write_text(content)
        try:
            os.chmod(self.settings.game.env_file, 0o640)
        except PermissionError:
            pass


async def attach_registry(app, lifespan_ctx: Lifespan) -> None:
    app.state.registry = lifespan_ctx.registry
    app.state.lifespan = lifespan_ctx
