import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type TelegramInfo } from "../lib/api";

const ALL_EVENTS = [
  ["down", "Servidor caído / reinicio"],
  ["restart", "Reinicio manual o programado"],
  ["resources", "CPU / RAM / disco por encima del umbral"],
  ["maintenance", "Avisos a jugadores antes de mantenimiento"],
  ["update", "Actualizaciones del juego"],
  ["backup", "Backups OK o fallidos"],
  ["join", "Jugador entra (OFF por defecto)"],
  ["leave", "Jugador sale (OFF por defecto)"],
  ["death", "Muerte de personaje (OFF por defecto)"],
  ["badpass", "Contraseña incorrecta (OFF por defecto)"],
] as const;

const DEFAULT_ON = new Set(["down", "restart", "resources", "maintenance", "update", "backup"]);

export function Notifications() {
  const toast = useApp((s) => s.notify);
  const [t, setT] = useState<TelegramInfo | null>(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [chats, setChats] = useState<Array<{ id: number; title: string; type: string }>>([]);

  async function load() {
    const info = await api.telegram();
    setT(info);
  }
  useEffect(() => { load().catch(() => {}); }, []);

  function toggle(ev: string) {
    if (!t) return;
    setT({
      ...t,
      events: t.events.includes(ev) ? t.events.filter((x) => x !== ev) : [...t.events, ev],
    });
  }

  async function save() {
    if (!t) return;
    setBusy(true);
    try {
      await api.saveTelegram({ token, chat_id: t.chat_id, enabled: t.enabled, events: t.events });
      toast("ok", "Notificador guardado");
      setToken("");
      await load();
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally { setBusy(false); }
  }

  async function detect() {
    try {
      const list = await api.telegramDetect();
      setChats(list);
      toast("ok", `${list.length} chats detectados`);
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  async function test() {
    try {
      const r = await api.telegramTest();
      toast(r.ok ? "ok" : "err", r.ok ? "Mensaje de prueba enviado" : "No se pudo enviar");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  if (!t) return <div className="card">Cargando…</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Notificaciones Telegram</h1>
      <div className="card space-y-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className="label">Token del bot</label>
            <input className="input" placeholder={t.token || "123456:AAA…"} value={token}
              onChange={(e) => setToken(e.target.value)} />
            <div className="mt-1 text-xs text-vh-muted">
              Estado actual: {t.configured ? `configurado (${t.token})` : "sin token"}
            </div>
          </div>
          <div>
            <label className="label">Chat ID del grupo</label>
            <input className="input" placeholder="-100xxxxxxxxxx" value={t.chat_id}
              onChange={(e) => setT({ ...t, chat_id: e.target.value })} />
            <button className="btn mt-2" onClick={detect}>Detectar chats (añade el bot al grupo y mándale /start)</button>
            {chats.length > 0 ? (
              <ul className="mt-2 max-h-32 overflow-y-auto rounded-md border border-vh-border bg-vh-bg p-2 text-xs scrollbar-thin">
                {chats.map((c) => (
                  <li key={c.id} className="flex justify-between">
                    <span>{c.title || c.type}</span>
                    <button className="badge" onClick={() => setT({ ...t, chat_id: String(c.id) })}>
                      usar {c.id}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={t.enabled}
            onChange={(e) => setT({ ...t, enabled: e.target.checked })} />
          Activar notificador
        </label>
        <div>
          <label className="label">Eventos activos</label>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {ALL_EVENTS.map(([k, label]) => {
              const on = t.events.includes(k) || (!t.events.length && DEFAULT_ON.has(k));
              return (
                <label key={k} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={on} onChange={() => toggle(k)} />
                  <span className="font-mono text-xs text-vh-muted">{k}</span>
                  <span>{label}</span>
                </label>
              );
            })}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-primary" disabled={busy} onClick={save}>Guardar</button>
          <button className="btn" onClick={test}>Mensaje de prueba</button>
        </div>
      </div>
      <div className="card text-xs text-vh-muted space-y-1">
        <p>
          El bot solo envía mensajes al grupo: no hay <code>getUpdates</code> ni puerto abierto
          en el panel. La cola de envío respeta los límites de la API (≈1 msg/s, ≤20/min/grupo)
          y aplica cooldown por tipo para evitar spam.
        </p>
      </div>
    </div>
  );
}
