"""Routers REST."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import bcrypt
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.schemas import (
    ChangePasswordIn,
    GameConfigIn,
    ListIn,
    LoginIn,
    ModifiersIn,
    NetworkIn,
    ScheduleIn,
    TelegramIn,
    WorldIn,
)
from app.core.config import get_settings, reload_settings
from app.core.registry import Registry, get_registry
from app.core.security import (
    LoginRateLimiter,
    auth_dependency,
    clear_session,
    client_key,
    get_key,
    hash_password,
    read_admin_hash,
    set_session,
    verify_password,
)
from app.services.args import build_argv, diff, parse_env_argv, validate_game, validate_modifiers
from app.core.util import is_platform_id, is_steamid64, mask_token, safe_read_text, validate_password

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
limiter = LoginRateLimiter(get_settings().panel.login_rate_limit_per_min)


@router.post("/auth/login")
async def login(payload: LoginIn, request: Request) -> JSONResponse:
    password = payload.password
    if not limiter.check(client_key(request)):
        raise HTTPException(429, "Demasiados intentos")
    settings = get_settings().panel
    hashed = read_admin_hash(settings.admin_password_hash_file)
    if not verify_password(password, hashed):
        raise HTTPException(401, "Contraseña incorrecta")
    response = JSONResponse(content={"ok": True})
    set_session(response, settings, get_key(settings))
    return response


@router.post("/auth/logout")
async def logout(response: JSONResponse, _: dict = Depends(auth_dependency)):
    clear_session(response)
    return {"ok": True}


@router.get("/auth/me")
async def me(_: dict = Depends(auth_dependency)):
    return {"user": "admin"}


@router.post("/auth/password")
async def change_password(payload: ChangePasswordIn, _: dict = Depends(auth_dependency)):
    settings = get_settings().panel
    hashed = read_admin_hash(settings.admin_password_hash_file)
    if not verify_password(payload.current, hashed):
        raise HTTPException(401, "Contraseña actual incorrecta")
    new_hash = hash_password(payload.new)
    settings.admin_password_hash_file.write_bytes(new_hash)
    os.chmod(settings.admin_password_hash_file, 0o600)
    return {"ok": True}


@router.get("/status")
async def status(reg: Registry = Depends(get_registry),
                 _: dict = Depends(auth_dependency)):
    server_state = await reg.process.status()
    return {
        "server": reg.process.snapshot(),
        "server_state": server_state.value,
        "roster": reg.parser.snapshot(),
        "a2s": reg.a2s.last,
        "metrics": reg.metrics.latest(),
        "version": await reg.updates.steam.installed_version(),
        "join_code": reg.parser.roster.last_join_code,
    }


@router.post("/server/start")
async def start(reg: Registry = Depends(get_registry),
                _: dict = Depends(auth_dependency)):
    await reg.process.start()
    return {"ok": True}


@router.post("/server/stop")
async def stop(reg: Registry = Depends(get_registry),
               _: dict = Depends(auth_dependency)):
    await reg.process.stop()
    return {"ok": True}


@router.post("/server/restart")
async def restart(payload: dict[str, Any] = Body(default={}),
                  reg: Registry = Depends(get_registry),
                  _: dict = Depends(auth_dependency)):
    countdown = int((payload or {}).get("countdown", 0))
    reason = (payload or {}).get("reason", "manual")
    await reg.process.restart(reason=reason, countdown_seconds=countdown)
    return {"ok": True}


@router.get("/server/argv")
async def get_argv(reg: Registry = Depends(get_registry),
                   _: dict = Depends(auth_dependency)):
    settings = get_settings()
    return {
        "active": parse_env_argv(settings.game.env_file),
        "pending": " ".join(build_argv(settings.game, settings.modifiers)),
    }


@router.post("/server/argv/preview")
async def preview_argv(payload: GameConfigIn, reg: Registry = Depends(get_registry),
                       _: dict = Depends(auth_dependency)):
    from app.core.config import GameSettings, ModifiersSettings
    settings = get_settings()
    g = GameSettings(**{**settings.game.model_dump(), **payload.model_dump()})
    ok, msg = validate_game(g)
    if not ok:
        raise HTTPException(400, msg)
    argv = build_argv(g, settings.modifiers)
    return {"argv": argv, "ok": ok, "message": msg}


@router.post("/server/config")
async def save_config(payload: GameConfigIn, reg: Registry = Depends(get_registry),
                      _: dict = Depends(auth_dependency)):
    settings = get_settings()
    g = settings.game.model_copy(update=payload.model_dump())
    ok, msg = validate_game(g)
    if not ok:
        raise HTTPException(400, msg)
    settings.game = g
    _write_env(settings)
    await reg.audit.log("game.config", payload.model_dump())
    return {"ok": True, "argv": build_argv(settings.game, settings.modifiers)}


@router.get("/modifiers")
async def get_modifiers(_: dict = Depends(auth_dependency)):
    return get_settings().modifiers.model_dump()


@router.post("/modifiers/preview")
async def preview_modifiers(payload: ModifiersIn, reg: Registry = Depends(get_registry),
                            _: dict = Depends(auth_dependency)):
    settings = get_settings()
    m = settings.modifiers.model_copy(update=payload.model_dump())
    ok, msg = validate_modifiers(m)
    if not ok:
        raise HTTPException(400, msg)
    pending = build_argv(settings.game, m)
    active_text = parse_env_argv(settings.game.env_file)
    active = _tokenize(active_text)
    return {"pending": pending, "diff": diff(active, pending), "ok": ok, "message": msg}


@router.post("/modifiers/apply")
async def apply_modifiers(payload: ModifiersIn, reg: Registry = Depends(get_registry),
                          _: dict = Depends(auth_dependency)):
    settings = get_settings()
    m = settings.modifiers.model_copy(update=payload.model_dump())
    ok, msg = validate_modifiers(m)
    if not ok:
        raise HTTPException(400, msg)
    if reg.settings.backup.pre_modifier_change:
        try:
            await reg.backups.create(reason="pre-modifier")
        except Exception as exc:
            log.warning("pre-modifier backup falló: %s", exc)
    settings.modifiers = m
    _write_env(settings)
    await reg.process.reload_unit()
    await reg.audit.log("modifiers.apply", m.model_dump())
    await reg.notifier.event("maintenance", {"minutes": 0, "reason": "aplicando modificadores"})
    await reg.process.restart(reason="modifier-change", countdown_seconds=30)
    return {"ok": True, "argv": build_argv(settings.game, settings.modifiers)}


@router.get("/worlds")
async def list_worlds(_: dict = Depends(auth_dependency), reg: Registry = Depends(get_registry)):
    return [w.snapshot() for w in reg.worlds.list()]


@router.post("/worlds")
async def create_world(payload: WorldIn, reg: Registry = Depends(get_registry),
                       _: dict = Depends(auth_dependency)):
    try:
        w = reg.worlds.create(payload.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    await reg.audit.log("world.create", {"name": payload.name})
    return w.snapshot()


@router.get("/lists")
async def get_lists(_: dict = Depends(auth_dependency), reg: Registry = Depends(get_registry)):
    return reg.lists.all()


@router.put("/lists/{name}")
async def put_list(name: str, payload: ListIn, reg: Registry = Depends(get_registry),
                   _: dict = Depends(auth_dependency)):
    if name not in ("adminlist.txt", "bannedlist.txt", "permittedlist.txt"):
        raise HTTPException(404)
    n, invalid = reg.lists.write(name, payload.entries)
    from app.services.audit import AuditService
    await AuditService(reg.db).log("list.update", {"name": name, "count": n, "invalid": invalid})
    return {"count": n, "invalid": invalid}


@router.get("/backups")
async def list_backups(_: dict = Depends(auth_dependency), reg: Registry = Depends(get_registry)):
    return [b.snapshot() for b in await reg.backups.list()]


@router.post("/backups")
async def create_backup(payload: dict[str, Any] = Body(default={}),
                        reg: Registry = Depends(get_registry),
                        _: dict = Depends(auth_dependency)):
    reason = (payload or {}).get("reason", "manual")
    try:
        b = await reg.backups.create(reason=reason)
    except Exception as exc:
        raise HTTPException(500, str(exc))
    return b.snapshot()


@router.post("/backups/{bid}/restore")
async def restore_backup(bid: int, reg: Registry = Depends(get_registry),
                         _: dict = Depends(auth_dependency)):
    try:
        ok = await reg.backups.restore(bid)
    except Exception as exc:
        raise HTTPException(500, str(exc))
    if not ok:
        raise HTTPException(404, "Backup no encontrado")
    return {"ok": True}


@router.get("/updates")
async def check_update(_: dict = Depends(auth_dependency), reg: Registry = Depends(get_registry)):
    return await reg.updates.check()


@router.post("/updates/run")
async def run_update(_: dict = Depends(auth_dependency), reg: Registry = Depends(get_registry)):
    result = await reg.updates.run()
    await reg.notifier.event(
        "update_ok" if result["returncode"] == "0" else "update_fail",
        {"version": result.get("installed", "?"), "error": result.get("tail", "")[:200]},
    )
    return result


@router.get("/metrics/history")
async def metrics_history(minutes: int = 60, _: dict = Depends(auth_dependency),
                          reg: Registry = Depends(get_registry)):
    return reg.metrics.history(minutes=minutes)


@router.get("/metrics/current")
async def metrics_current(_: dict = Depends(auth_dependency),
                          reg: Registry = Depends(get_registry)):
    return reg.metrics.latest()


@router.get("/logs/recent")
async def logs_recent(limit: int = 200, _: dict = Depends(auth_dependency),
                      reg: Registry = Depends(get_registry)):
    return {"lines": reg.logstream.recent(limit=limit)}


@router.get("/audit")
async def audit_log(limit: int = 200, _: dict = Depends(auth_dependency),
                    reg: Registry = Depends(get_registry)):
    from app.services.audit import AuditService
    return await AuditService(reg.db).list(limit=limit)


@router.get("/schedule")
async def get_schedule(_: dict = Depends(auth_dependency)):
    return get_settings().schedule.model_dump()


@router.post("/schedule")
async def save_schedule(payload: ScheduleIn, reg: Registry = Depends(get_registry),
                        _: dict = Depends(auth_dependency)):
    settings = get_settings()
    settings.schedule = settings.schedule.model_copy(update=payload.model_dump())
    await reg.audit.log("schedule.update", payload.model_dump())
    await reg.scheduler.stop()
    await reg.scheduler.start()
    return {"ok": True}


@router.get("/telegram")
async def get_telegram(_: dict = Depends(auth_dependency)):
    s = get_settings().telegram
    return {
        "enabled": s.enabled,
        "chat_id": s.chat_id,
        "events": s.events,
        "token": mask_token(s.token),
        "configured": bool(s.token and s.chat_id),
    }


@router.post("/telegram")
async def save_telegram(payload: TelegramIn, reg: Registry = Depends(get_registry),
                        _: dict = Depends(auth_dependency)):
    settings = get_settings()
    token = payload.token.strip()
    if token == mask_token(settings.telegram.token):
        token = settings.telegram.token
    settings.telegram = settings.telegram.model_copy(update={
        "token": token, "chat_id": payload.chat_id.strip(),
        "enabled": payload.enabled, "events": payload.events,
    })
    await reg.audit.log("telegram.update", {"chat_id": payload.chat_id, "enabled": payload.enabled})
    await reg.notifier.close()
    reg.notifier = type(reg.notifier)(settings)
    await reg.notifier.start()
    return {"ok": True}


@router.post("/telegram/test")
async def telegram_test(_: dict = Depends(auth_dependency),
                        reg: Registry = Depends(get_registry)):
    ok = await reg.notifier.test()
    return {"ok": ok}


@router.post("/telegram/detect")
async def telegram_detect(_: dict = Depends(auth_dependency)):
    n = Notifier(get_settings())
    return await n.detect_chat()


@router.get("/network")
async def get_network(_: dict = Depends(auth_dependency)):
    settings = get_settings()
    s = settings.network
    g = settings.game
    return {
        "public_host": s.public_host,
        "use_a2s": s.use_a2s,
        "a2s_probe_interval_seconds": s.a2s_probe_interval_seconds,
        "join_ip_url": f"{s.public_host}:{g.port}" if s.public_host else "",
        "steam_favorites_url": f"{s.public_host}:{g.port + 1}" if s.public_host else "",
        "join_code": None,
    }


@router.post("/network")
async def save_network(payload: NetworkIn, reg: Registry = Depends(get_registry),
                       _: dict = Depends(auth_dependency)):
    settings = get_settings()
    settings.network = settings.network.model_copy(update=payload.model_dump())
    await reg.a2s.stop()
    await reg.a2s.start()
    await reg.audit.log("network.update", payload.model_dump())
    return {"ok": True}


@router.get("/telegram/events")
async def telegram_events(_: dict = Depends(auth_dependency)):
    return {
        "down", "restart", "resources", "maintenance", "update", "backup",
        "join", "leave", "death", "badpass",
    }


def _write_env(settings) -> None:
    from app.services.args import build_argv
    argv = build_argv(settings.game, settings.modifiers)
    content = (
        "# Generado por valheim-dashboard. Se sobrescribe al aplicar cambios.\n"
        "ARGV=" + " ".join(f'"{a}"' if " " in a else a for a in argv) + "\n"
    )
    settings.game.env_file.write_text(content)
    try:
        os.chmod(settings.game.env_file, 0o640)
    except OSError:
        pass


def _tokenize(text: str) -> list[str]:
    import shlex
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()
