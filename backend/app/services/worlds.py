"""Gestión de mundos. Consciente del formato 1.0 (carpeta) y del legado
(``<mundo>.db`` + ``<mundo>.fwl``).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_NEW_DIR_RE = re.compile(r"^_main\.\d+\.fwl2$")
_LEGACY_RE = re.compile(r"^(?P<name>.+)\.(db|fwl)$")


@dataclass
class WorldInfo:
    name: str
    path: Path
    format: str
    size: int
    last_modified: float
    generation: int | None = None
    last_save_ok: bool = False
    empty: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "format": self.format,
            "size_bytes": self.size,
            "last_modified": self.last_modified,
            "generation": self.generation,
            "last_save_ok": self.last_save_ok,
            "empty": self.empty,
        }


class WorldService:
    def __init__(self, savedir: Path) -> None:
        self.savedir = savedir
        self.worlds_dir = savedir / "worlds_local"

    def list(self) -> list[WorldInfo]:
        if not self.worlds_dir.is_dir():
            return []
        legacy_names: set[str] = set()
        for entry in self.worlds_dir.iterdir():
            if entry.is_file() and entry.suffix in {".db", ".fwl"}:
                name = _LEGACY_RE.match(entry.name)
                if name:
                    legacy_names.add(name.group("name"))
        out: list[WorldInfo] = []
        seen_legacy: set[str] = set()
        for entry in sorted(self.worlds_dir.iterdir()):
            if entry.is_dir():
                if entry.name in legacy_names:
                    continue
                w = self._inspect_dir(entry)
                if w:
                    out.append(w)
            elif entry.is_file() and entry.suffix in {".db", ".fwl"}:
                w = self._inspect_legacy(entry)
                if w and w.name not in seen_legacy:
                    seen_legacy.add(w.name)
                    out.append(w)
        return out

    def _inspect_dir(self, path: Path) -> WorldInfo | None:
        files = list(path.iterdir())
        if not files:
            return WorldInfo(name=path.name, path=path, format="v10",
                             size=0, last_modified=path.stat().st_mtime,
                             empty=True)
        total = sum(f.stat().st_size for f in files if f.is_file())
        last = max(f.stat().st_mtime for f in files if f.is_file())
        fwl_files = [f for f in files if _NEW_DIR_RE.match(f.name)]
        generation: int | None = None
        for f in fwl_files:
            m = re.search(r"_main\.(\d+)\.fwl2", f.name)
            if m:
                generation = max(generation or 0, int(m.group(1)))
        ok = any(re.match(r"_main\.\d+\.ok", f.name) for f in files)
        return WorldInfo(
            name=path.name, path=path, format="v10",
            size=total, last_modified=last,
            generation=generation, last_save_ok=ok, empty=False,
        )

    def _inspect_legacy(self, path: Path) -> WorldInfo | None:
        m = _LEGACY_RE.match(path.name)
        if not m:
            return None
        name = m.group("name")
        sibling_db = path.with_suffix(".db")
        if not sibling_db.is_file():
            return None
        size = path.stat().st_size + sibling_db.stat().st_size
        return WorldInfo(
            name=name, path=path, format="legacy",
            size=size, last_modified=max(path.stat().st_mtime,
                                         sibling_db.stat().st_mtime),
            empty=False, last_save_ok=True,
        )

    def exists(self, name: str) -> bool:
        return any(w.name == name for w in self.list())

    def rename(self, old: str, new: str) -> None:
        if not re.match(r"^[A-Za-z0-9 _\-]{1,40}$", new):
            raise ValueError("Nombre de mundo inválido")
        for entry in self.worlds_dir.iterdir():
            if entry.name == old:
                entry.rename(entry.with_name(new))
                return
        raise FileNotFoundError(old)

    def create(self, name: str) -> WorldInfo:
        if not re.match(r"^[A-Za-z0-9 _\-]{1,40}$", name):
            raise ValueError("Nombre de mundo inválido")
        (self.worlds_dir / name).mkdir(parents=False, exist_ok=True)
        return self._inspect_dir(self.worlds_dir / name) or WorldInfo(
            name=name, path=self.worlds_dir / name, format="v10",
            size=0, last_modified=time.time(), empty=True,
        )
