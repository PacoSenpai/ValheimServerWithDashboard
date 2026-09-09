"""Wrapper sobre ``steamcmd`` para instalar y actualizar el servidor
(Steam AppID 896660).
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import Settings

log = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"(?:buildid|BuildID|app build)\s*[:=]\s*(\d+)")
_VERSION_STR_RE = re.compile(r"\"public\"\s+\"buildid\"\s+\"(\d+)\"")


class SteamService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.install_dir = settings.game.install_dir
        self._steamcmd = self._detect_steamcmd()

    def _detect_steamcmd(self) -> list[str]:
        for c in ("/usr/games/steamcmd", "/usr/bin/steamcmd"):
            if Path(c).is_file():
                return [c]
        return ["steamcmd"]

    async def installed_version(self) -> str:
        version_file = self.install_dir / "steamapps" / "appmanifest_896660.acf"
        if not version_file.is_file():
            return "no instalado"
        text = version_file.read_text(encoding="utf-8", errors="replace")
        for pat in (_VERSION_RE, _VERSION_STR_RE):
            m = pat.search(text)
            if m:
                return m.group(1)
        return "desconocido"

    async def install_or_update(self) -> tuple[int, str]:
        self.install_dir.mkdir(parents=True, exist_ok=True)
        cmd = self._steamcmd + [
            "+force_install_dir", str(self.install_dir),
            "+login", "anonymous",
            "+app_update", "896660", "validate",
            "+quit",
        ]
        log.info("steamcmd: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        text = (stdout or b"").decode("utf-8", "replace", errors="replace")
        return proc.returncode or 0, text

    async def is_up_to_date(self) -> tuple[bool, str]:
        cmd = self._steamcmd + [
            "+force_install_dir", str(self.install_dir),
            "+login", "anonymous",
            "+app_info_update", "1",
            "+app_info_print", "896660",
            "+quit",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        text = (stdout or b"").decode("utf-8", "replace", errors="replace")
        current = await self.installed_version()
        return current in text, current
