"""Comprobación y aplicación de actualizaciones con pre-backup."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.backups import BackupService
from app.services.steam import SteamService

log = logging.getLogger(__name__)


class UpdateService:
    def __init__(self, settings: Settings, steam: SteamService, backups: BackupService) -> None:
        self.settings = settings
        self.steam = steam
        self.backups = backups

    async def check(self) -> dict[str, str]:
        installed = await self.steam.installed_version()
        ok, _ = await self.steam.is_up_to_date()
        return {
            "installed": installed,
            "up_to_date": "sí" if ok else "no",
        }

    async def run(self) -> dict[str, str]:
        if self.settings.backup.pre_update:
            await self.backups.create(reason="pre-update")
        code, output = await self.steam.install_or_update()
        installed = await self.steam.installed_version()
        return {
            "installed": installed,
            "returncode": str(code),
            "tail": "\n".join(output.splitlines()[-15:]),
        }
