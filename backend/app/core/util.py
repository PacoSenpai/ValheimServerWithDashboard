"""Utilidades comunes."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORLD_NAME_RE = re.compile(r"^[A-Za-z0-9 _\-]{1,40}$")
PASSWORD_RE = re.compile(r"^[^@!\x22\x27]{5,40}$")
STEAMID64_RE = re.compile(r"^\d{17}$")
PLATFORM_ID_RE = re.compile(r"^\[[^\]]+\]_[A-Za-z0-9\-]{4,40}$")

DISALLOWED_PASSWORD_CHARS = set('"@!\' \t\r\n')

ALL_TELEGRAM_EVENTS = {
    "down", "restart", "resources", "maintenance",
    "update", "backup", "join", "leave", "death", "badpass",
}


def utcnow() -> int:
    return int(time.time())


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_steamid64(s: str) -> bool:
    return bool(STEAMID64_RE.match(s.strip()))


def is_platform_id(s: str) -> bool:
    return bool(PLATFORM_ID_RE.match(s.strip()))


def is_world_name(s: str) -> bool:
    return bool(WORLD_NAME_RE.match(s))


def validate_password(password: str, world: str) -> tuple[bool, str]:
    if len(password) < 5 or len(password) > 40:
        return False, "La contraseña debe tener entre 5 y 40 caracteres"
    if any(c in DISALLOWED_PASSWORD_CHARS for c in password):
        return False, 'La contraseña no puede contener " @ ! ni espacios'
    if world and world.lower() in password.lower():
        return False, "La contraseña no puede contener el nombre del mundo"
    return True, ""


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def mask_token(token: str) -> str:
    if not token or ":" not in token:
        return "***"
    left, _ = token.split(":", 1)
    return f"{left}:***"


def chunks(data: list[Any], size: int):
    for i in range(0, len(data), size):
        yield data[i:i + size]
