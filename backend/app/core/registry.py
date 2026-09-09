"""Registro de servicios accesibles desde la API y WS.

Los servicios se crean en ``Lifespan.startup`` y se exponen en
``app.state.registry``. Los routers los recuperan vía dependencia
``Depends(get_registry)``.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.config import Settings
from app.core.db import Database
from app.core.events import EventBus
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
from app.services.updates import UpdateService
from app.services.worlds import WorldService


@dataclass
class Registry:
    settings: Settings
    db: Database
    bus: EventBus
    audit: AuditService
    process: ProcessService
    backups: BackupService
    updates: UpdateService
    metrics: MetricsService
    worlds: WorldService
    lists: ListService
    logstream: LogStream
    parser: PlayerEventHandler
    a2s: A2SProbe
    scheduler: SchedulerService
    notifier: Notifier


def get_registry(request: Request) -> Registry:
    return request.app.state.registry


def get_registry_from_websocket(websocket) -> Registry:
    return websocket.app.state.registry
