import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api } from "../lib/api";

export function Updates() {
  const toast = useApp((s) => s.notify);
  const [info, setInfo] = useState<{ installed: string; up_to_date: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [tail, setTail] = useState<string | null>(null);

  async function load() { setInfo(await api.updates()); }
  useEffect(() => { load().catch((e) => toast("err", e?.message || String(e))); }, [toast]);

  async function run() {
    setBusy(true);
    setTail(null);
    try {
      const r = await api.runUpdate();
      setTail(r.tail);
      toast(r.returncode === "0" ? "ok" : "err",
        r.returncode === "0" ? `Actualizado a ${r.installed}` : "Falló la actualización");
      await load();
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Actualizaciones</h1>
      <div className="card flex items-center justify-between">
        <div className="text-sm">
          <div>Versión instalada (build ID): <strong>{info?.installed ?? "?"}</strong></div>
          <div className="text-xs text-vh-muted">
            {info?.up_to_date === "sí" ? "Al día" : "Hay una versión más reciente disponible"}
          </div>
        </div>
        <button className="btn btn-primary" disabled={busy} onClick={run}>
          {busy ? "Actualizando…" : "Actualizar ahora"}
        </button>
      </div>
      <div className="card text-xs text-vh-muted">
        Antes de actualizar, el panel hace un backup automático del savedir y reinicia el
        servidor. Si tienes mods, espera a que los autores publiquen la build compatible con
        1.0.
      </div>
      {tail ? (
        <div className="card">
          <div className="text-sm font-semibold">Salida de steamcmd</div>
          <pre className="mt-2 max-h-72 overflow-y-auto rounded-md bg-vh-bg p-2 text-[11px] leading-relaxed scrollbar-thin">
            {tail}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
