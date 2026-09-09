"""Cliente de Telegram con rate limit, cola, reintentos y dedupe/cooldown."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

import httpx

from app.core.config import TelegramSettings, get_settings

log = logging.getLogger(__name__)

TEMPLATES: dict[str, str] = {
    "down": "🔴 <b>Servidor caído</b>\n{error}",
    "up": "🟢 <b>Servidor listo</b>\n{version}",
    "restart": "🔁 <b>Reinicio</b>: {reason}",
    "crash": "💥 <b>Crash-loop</b>: {count} caídas en {minutes} min",
    "resources": "⚠️ <b>{kind}</b>: {value:.0f}% (umbral {threshold:.0f}%)",
    "resources_ok": "✅ <b>{kind}</b> de vuelta a la normalidad ({value:.0f}%)",
    "update_available": "⬇️ <b>Update disponible</b>: {version}",
    "update_ok": "✅ <b>Actualizado</b> a {version}",
    "update_fail": "❌ <b>Error actualizando</b>: {error}",
    "backup_ok": "💾 <b>Backup OK</b> ({size} MB)",
    "backup_fail": "❌ <b>Backup fallido</b>: {error}",
    "restore_ok": "♻️ <b>Restaurado</b> desde backup {id}",
    "maintenance": "⏰ <b>Mantenimiento en {minutes} min</b>: {reason}",
    "join": "➡️ <b>{name}</b> se ha conectado",
    "leave": "⬅️ <b>{name}</b> se ha desconectado",
    "death": "☠️ <b>{name}</b> ha muerto",
    "badpass": "🚫 Contraseña incorrecta (SteamID …{steam_id})",
}


class Notifier:
    def __init__(self, settings=None) -> None:
        self.settings: TelegramSettings = (settings or get_settings()).telegram
        self._client: httpx.AsyncClient | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._last_sent: dict[str, float] = defaultdict(float)
        self._recent: list[dict[str, Any]] = []

    async def start(self) -> None:
        if not self.settings.enabled or not self.settings.token or not self.settings.chat_id:
            log.info("Notificador desactivado (falta token/chat_id)")
            return
        self._client = httpx.AsyncClient(timeout=self.settings.timeout_seconds)
        self._worker = asyncio.create_task(self._run(), name="notifier")
        log.info("Notificador Telegram activo")

    async def close(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except (asyncio.CancelledError, Exception):
                pass
        if self._client:
            await self._client.aclose()

    def is_active(self) -> bool:
        return self._client is not None

    async def event(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        if kind not in self.settings.events and kind not in {"up", "crash", "resources_ok",
                                                              "restore_ok", "update_ok",
                                                              "update_fail", "restart"}:
            return
        if not self.is_active():
            return
        payload = payload or {}
        template = TEMPLATES.get(kind)
        if not template:
            return
        try:
            text = template.format(**payload)
        except KeyError:
            text = template
        dedupe_key = f"{kind}:{sorted(payload.items())}"
        if time.time() - self._last_sent[dedupe_key] < self.settings.cooldown_seconds:
            return
        self._last_sent[dedupe_key] = time.time()
        self._recent.append({"ts": time.time(), "kind": kind, "text": text})
        self._recent = self._recent[-200:]
        await self._queue.put({"kind": kind, "text": text, "payload": payload})

    async def test(self) -> bool:
        if not self.is_active():
            return False
        return await self._send("✅ <b>Test</b> desde valheim-dashboard")

    async def detect_chat(self) -> list[dict[str, Any]]:
        if not self.settings.token:
            return []
        url = f"https://api.telegram.org/bot{self.settings.token}/getUpdates"
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
        data = r.json()
        chats: list[dict[str, Any]] = []
        for upd in data.get("result", []):
            ch = (upd.get("message") or upd.get("my_chat_member") or {}).get("chat")
            if ch:
                chats.append({"id": ch.get("id"), "title": ch.get("title") or ch.get("username"),
                              "type": ch.get("type")})
        seen: set[Any] = set()
        out: list[dict[str, Any]] = []
        for chat in chats:
            if chat["id"] in seen:
                continue
            seen.add(chat["id"])
            out.append(chat)
        return out

    async def _run(self) -> None:
        window: list[float] = []
        while True:
            item = await self._queue.get()
            now = time.time()
            window = [t for t in window if now - t < 60]
            if len(window) >= self.settings.rate_limit_per_minute:
                await asyncio.sleep(1.0)
                window = [t for t in window if time.time() - t < 60]
            window.append(time.time())
            ok = await self._send(item["text"])
            if not ok:
                await asyncio.sleep(2.0)

    async def _send(self, text: str) -> bool:
        if not self._client or not self.settings.token or not self.settings.chat_id:
            return False
        url = f"https://api.telegram.org/bot{self.settings.token}/sendMessage"
        for attempt in range(self.settings.max_retries):
            try:
                r = await self._client.post(url, json={
                    "chat_id": self.settings.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
                if r.status_code == 200 and r.json().get("ok"):
                    return True
                log.warning("Telegram %s: %s", r.status_code, r.text[:200])
            except Exception as exc:
                log.warning("Telegram intento %d: %s", attempt, exc)
            await asyncio.sleep(2 ** attempt)
        return False

    def recent(self) -> list[dict[str, Any]]:
        return list(self._recent)
