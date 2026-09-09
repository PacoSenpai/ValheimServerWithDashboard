import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type GameConfig } from "../lib/api";

export function Config() {
  const toast = useApp((s) => s.notify);
  const [cfg, setCfg] = useState<GameConfig | null>(null);
  const [argv, setArgv] = useState<string>("");

  useEffect(() => {
    Promise.all([api.argv(), api.me()]).then(async ([a]) => {
      setArgv(a.active);
      const status = await api.status();
      setCfg({
        name: (status.server as any).name || "Mi Valheim Server",
        world: (status.server as any).world || "Dedicated",
        password: (status.server as any).password || "",
        port: (status.server as any).port || 2456,
        public: (status.server as any).public ?? true,
        crossplay: (status.server as any).crossplay ?? false,
        save_interval: (status.server as any).save_interval || 1800,
        extra_args: (status.server as any).extra_args || [],
      });
    }).catch((e) => toast("err", String(e)));
  }, [toast]);

  if (!cfg) return <div className="card">Cargando…</div>;

  async function save() {
    if (!cfg) return;
    try {
      const r = await api.saveConfig(cfg);
      setArgv(r.argv.join(" "));
      toast("ok", "Configuración guardada. Cambios en la próxima reinicio.");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  async function restart() {
    try {
      await api.restart(15, "config-change");
      toast("ok", "Reinicio en 15s");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Configuración del servidor</h1>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="card space-y-3">
          <div>
            <label className="label">Nombre del servidor</label>
            <input className="input" value={cfg.name}
              onChange={(e) => setCfg({ ...cfg, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Nombre del mundo</label>
            <input className="input" value={cfg.world}
              onChange={(e) => setCfg({ ...cfg, world: e.target.value })} />
          </div>
          <div>
            <label className="label">Contraseña (≥5, sin " @ !)</label>
            <input className="input" type="text" value={cfg.password}
              onChange={(e) => setCfg({ ...cfg, password: e.target.value })} />
          </div>
          <div>
            <label className="label">Puerto (1024-65535)</label>
            <input className="input" type="number" value={cfg.port}
              onChange={(e) => setCfg({ ...cfg, port: Number(e.target.value) })} />
          </div>
          <div>
            <label className="label">Auto-guardado (segundos)</label>
            <input className="input" type="number" value={cfg.save_interval}
              onChange={(e) => setCfg({ ...cfg, save_interval: Number(e.target.value) })} />
          </div>
          <div className="flex items-center gap-6 pt-1">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={cfg.public}
                onChange={(e) => setCfg({ ...cfg, public: e.target.checked })} />
              Visible en la lista
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={cfg.crossplay}
                onChange={(e) => setCfg({ ...cfg, crossplay: e.target.checked })} />
              Modo crossplay
            </label>
          </div>
        </div>
        <div className="card">
          <div className="text-sm font-semibold">Argv activo</div>
          <pre className="mt-2 max-h-96 overflow-y-auto rounded-md bg-vh-bg p-3 text-xs leading-relaxed scrollbar-thin">
            {argv}
          </pre>
          <div className="mt-2 text-xs text-vh-muted">
            El cambio entra en vigor al reiniciar. El modo crossplay cambia
            el backend de red; Steam usa la lista de servidores, crossplay
            usa el join code de PlayFab.
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button className="btn btn-primary" onClick={save}>Guardar</button>
        <button className="btn" onClick={restart}>Guardar y reiniciar (15s)</button>
      </div>
    </div>
  );
}
