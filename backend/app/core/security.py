"""Autenticación: cookie httpOnly firmada con JWT."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, Request, Response, status

from app.core.config import PanelSettings, get_settings

log = logging.getLogger(__name__)
_SESSION_COOKIE = "vh_session"


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except ValueError:
        return False


def read_admin_hash(path: Path) -> bytes:
    if not path.is_file():
        raise HTTPException(500, "Panel no inicializado")
    return path.read_bytes()


def set_session(response: Response, settings: PanelSettings, key: bytes) -> None:
    ttl = settings.session_ttl_hours
    payload = {
        "sub": "admin",
        "iat": int(time.time()),
        "exp": datetime.now(UTC) + timedelta(hours=ttl),
    }
    token = jwt.encode(payload, key, algorithm="HS256")
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="strict",
        secure=False,
        max_age=ttl * 3600,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(_SESSION_COOKIE, path="/")


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(_SESSION_COOKIE)


def get_key(settings: PanelSettings) -> bytes:
    if not settings.secret_key_file.is_file():
        raise HTTPException(500, "Panel no inicializado")
    return settings.secret_key_file.read_bytes()


def require_session(request: Request) -> dict[str, Any]:
    settings = get_settings().panel
    token = get_session_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        payload = jwt.decode(token, get_key(settings), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión caducada") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida") from exc
    return payload


class LoginRateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        window = [t for t in self._hits[key] if now - t < 60]
        self._hits[key] = window
        if len(window) >= self.per_minute:
            return False
        window.append(now)
        return True


def client_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    digest = hmac.new(b"vh-panel", ua.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{host}:{digest}"


async def auth_dependency(request: Request) -> dict[str, Any]:
    return require_session(request)


AuthDep = Callable[[Request], Awaitable[dict[str, Any]]]
