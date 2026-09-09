"""Endpoints WebSocket para estado en vivo y consola."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.core.registry import get_registry_from_websocket
from app.core.security import LoginRateLimiter, get_key

log = logging.getLogger(__name__)

router = APIRouter()
_limiter = LoginRateLimiter(60)


async def _auth_ws(websocket: WebSocket) -> bool:
    token = websocket.cookies.get("vh_session")
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    try:
        jwt.decode(token, get_key(get_settings().panel), algorithms=["HS256"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    return True


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    if not await _auth_ws(websocket):
        return
    await websocket.accept()
    reg = get_registry_from_websocket(websocket)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
    topics = {"roster", "metrics", "a2s", "join_code", "alert", "player"}

    async def pump(topic: str) -> None:
        async for item in reg.bus.subscribe(topic):
            await queue.put({"topic": topic, "payload": item})

    tasks = [asyncio.create_task(pump(t)) for t in topics]
    try:
        await websocket.send_json({"topic": "snapshot", "payload": {
            "metrics": reg.metrics.latest(),
            "roster": reg.parser.snapshot(),
            "a2s": reg.a2s.last,
            "server": reg.process.snapshot(),
        }})
        while True:
            item = await queue.get()
            await websocket.send_json(item)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_live error")
    finally:
        for t in tasks:
            t.cancel()


@router.websocket("/ws/console")
async def ws_console(websocket: WebSocket):
    if not await _auth_ws(websocket):
        return
    await websocket.accept()
    reg = get_registry_from_websocket(websocket)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=512)

    async def feed() -> None:
        async for item in reg.bus.subscribe("log"):
            await queue.put(item)

    task = asyncio.create_task(feed())
    try:
        for line in reg.logstream.recent(200):
            await websocket.send_json({"line": line})
        while True:
            item = await queue.get()
            await websocket.send_json(item)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_console error")
    finally:
        task.cancel()
