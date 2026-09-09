import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type NetworkInfo } from "../lib/api";

export function Settings() {
  const toast = useApp((s) => s.notify);
  const logout = useApp((s) => s.logout);
  const [net, setNet] = useState<NetworkInfo | null>(null);
  const [audit, setAudit] = useState<Array<{ id: number; ts: number; action: string; payload: any }>>([]);
  const [pw, setPw] = useState({ current: "", new: "", confirm: "" });

  async function load() {
    const [n, a] = await Promise.all([api.network(), api.audit(50)]);
    setNet(n);
    setAudit(a);
  }
  useEffect(() => { load().catch((e) => toast("err", e?.message || String(e))); }, [toast]);

  async function saveNet() {
    if (!net) return;
    try {
      await api.saveNetwork({
        public_host: net.public_host,
        use_a2s: net.use_a2s,
        a2s_probe_interval_seconds: net.a2s_probe_interval_seconds,
      });
      toast("ok", "Red guardada");
    } catch (e: any) { toast("err", e?.message || String(e)); }
  }

  async function changePassword() {
    if (pw.new !== pw.confirm) { toast("err", "No coinciden"); return; }
    try {
      await api.changePassword(pw.current, pw.new);
      setPw({ current: "", new: "", confirm: "" });
      toast("ok", "Contraseña cambiada");
    } catch (e: any) { toast("err", e?.message || String(e)); }
  }

  if (!net) return <div className="card">Cargando…</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Ajustes</h1>

      <div className="card space-y-3">
        <div className="text-sm font-semibold">Red pública</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <label className="label">Dominio público (DDNS)</label>
            <input className="input" value={net.public_host}
              onChange={(e) => setNet({ ...net, public_host: e.target.value })}
              placeholder="wireguard-s9kvqmuzrbsijrkb5u3.pacoserver.cc" />
          </div>
          <div>
            <label className="label">A2S (sondar jugadores en vivo)</label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={net.use_a2s}
                onChange={(e) => setNet({ ...net, use_a2s: e.target.checked })} />
              Activar
            </label>
            <input className="input mt-2" type="number" value={net.a2s_probe_interval_seconds}
              onChange={(e) => setNet({ ...net, a2s_probe_interval_seconds: Number(e.target.value) })} />
            <div className="mt-1 text-xs text-vh-muted">Segundos entre sondeos. 5-15 recomendado.</div>
          </div>
        </div>
        <button className="btn btn-primary" onClick={saveNet}>Guardar red</button>
      </div>

      <div className="card space-y-3">
        <div className="text-sm font-semibold">Cambiar contraseña del panel</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input className="input" type="password" placeholder="Actual" value={pw.current}
            onChange={(e) => setPw({ ...pw, current: e.target.value })} />
          <input className="input" type="password" placeholder="Nueva (≥8)" value={pw.new}
            onChange={(e) => setPw({ ...pw, new: e.target.value })} />
          <input className="input" type="password" placeholder="Repetir" value={pw.confirm}
            onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
        </div>
        <button className="btn btn-primary" onClick={changePassword}>Cambiar</button>
      </div>

      <div className="card">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Auditoría (últimas {audit.length})</div>
          <button className="btn" onClick={logout}>Cerrar sesión</button>
        </div>
        <div className="mt-2 max-h-72 overflow-y-auto rounded-md bg-vh-bg p-2 text-xs scrollbar-thin">
          {audit.length === 0 ? (
            <div className="text-vh-muted">Sin entradas.</div>
          ) : (
            audit.map((a) => (
              <div key={a.id} className="border-b border-vh-border/50 py-1 last:border-0">
                <span className="text-vh-muted">{new Date(a.ts * 1000).toLocaleString()}</span>{" "}
                <span className="font-mono">{a.action}</span>{" "}
                <span className="text-vh-muted">{JSON.stringify(a.payload)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
