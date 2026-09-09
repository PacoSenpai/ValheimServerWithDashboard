"""Editor de ``adminlist.txt``, ``bannedlist.txt``, ``permittedlist.txt``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.util import is_platform_id, is_steamid64, safe_read_text

log = logging.getLogger(__name__)

LIST_FILES = ("adminlist.txt", "bannedlist.txt", "permittedlist.txt")


class ListService:
    def __init__(self, savedir: Path) -> None:
        self.savedir = savedir

    def _path(self, name: str) -> Path:
        if name not in LIST_FILES:
            raise ValueError(name)
        return self.savedir / name

    def read(self, name: str) -> list[str]:
        return [line for line in safe_read_text(self._path(name)).splitlines()
                if line.strip() and not line.startswith("#")]

    def write(self, name: str, entries: list[str]) -> tuple[int, list[str]]:
        seen: set[str] = set()
        clean: list[str] = []
        invalid: list[str] = []
        for raw in entries:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if not (is_steamid64(line) or is_platform_id(line)):
                invalid.append(line)
                continue
            if line in seen:
                continue
            seen.add(line)
            clean.append(line)
        self._path(name).write_text("\n".join(clean) + ("\n" if clean else ""))
        return len(clean), invalid

    def all(self) -> dict[str, list[str]]:
        return {n: self.read(n) for n in LIST_FILES}

    def validate(self, entries: list[str], crossplay: bool) -> list[str]:
        invalid: list[str] = []
        for raw in entries:
            line = raw.strip()
            if not line:
                continue
            ok = is_platform_id(line) if crossplay else is_steamid64(line)
            if not ok:
                invalid.append(line)
        return invalid
