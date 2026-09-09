import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type ScheduleInfo } from "../lib/api";

export function Schedule() {
  const toast = useApp((s) => s.notify);
  const [s, setS] = useState<ScheduleInfo | null>(null);

  useEffect(() => { api.schedule().then(setS).catch(() => {}); }, []);
  if (!s) return <div className="card">Cargando…</div>;

  async function save() {
    if (!s) return;
    try {
      await api.saveSchedule(s);
      toast("ok", "Programación guardada");
    } catch (e: any) { toast("err", e?.message || String(e)); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Programación</h1>
      <div className="card space-y-3">
        <div>
          <label className="label">Reinicio programado (cron, UTC)</label>
          <input className="input" placeholder="0 5 * * *" value={s.restart_cron}
            onChange={(e) => setS({ ...s, restart_cron: e.target.value })} />
          <div className="mt-1 text-xs text-vh-muted">
            Vacío = desactivado. Ej: <code>0 5 * * *</code> = cada día a las 05:00 UTC.
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className="label">Apagado por inactividad (min, 0 = desactivado)</label>
            <input className="input" type="number" min={0} value={s.idle_shutdown_minutes}
              onChange={(e) => setS({ ...s, idle_shutdown_minutes: Number(e.target.value) })} />
          </div>
          <div>
            <label className="label">Aviso previo por Telegram (min)</label>
            <input className="input" type="number" min={0} value={s.warn_before_restart_minutes}
              onChange={(e) => setS({ ...s, warn_before_restart_minutes: Number(e.target.value) })} />
          </div>
        </div>
        <button className="btn btn-primary" onClick={save}>Guardar</button>
      </div>
      <div className="card text-xs text-vh-muted">
        Los avisos a jugadores van al grupo de Telegram configurado. El servidor dedicado
        vanilla no permite broadcast in-game, así que este es el canal principal de aviso.
      </div>
    </div>
  );
}
