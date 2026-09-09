import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type WorldInfo } from "../lib/api";

export function Worlds() {
  const toast = useApp((s) => s.notify);
  const [items, setItems] = useState<WorldInfo[]>([]);
  const [name, setName] = useState("");

  async function load() { setItems(await api.worlds()); }
  useEffect(() => { load().catch((e) => toast("err", e?.message || String(e))); }, [toast]);

  async function create() {
    if (!name.trim()) return;
    try {
      await api.createWorld(name.trim());
      setName("");
      await load();
      toast("ok", `Mundo '${name}' creado`);
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Mundos</h1>
      <div className="card flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[240px]">
          <label className="label">Crear mundo</label>
          <input className="input" placeholder="MiMundo" value={name}
            onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={create}>Crear</button>
      </div>
      <div className="card">
        <div className="text-sm font-semibold">Existentes ({items.length})</div>
        {items.length === 0 ? (
          <div className="mt-2 text-xs text-vh-muted">No hay mundos en <code>worlds_local/</code>.</div>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead className="text-left text-xs uppercase text-vh-muted">
              <tr>
                <th className="py-1">Nombre</th>
                <th>Formato</th>
                <th>Tamaño</th>
                <th>Generación</th>
                <th>Última escritura</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {items.map((w) => (
                <tr key={w.name} className="border-t border-vh-border">
                  <td className="py-1.5 font-medium">{w.name}</td>
                  <td>{w.format === "v10" ? "1.0 (carpeta)" : "legado (.db/.fwl)"}</td>
                  <td>{humanBytes(w.size_bytes)}</td>
                  <td>{w.generation ?? "—"}</td>
                  <td>{new Date(w.last_modified * 1000).toLocaleString()}</td>
                  <td>
                    {w.empty ? (
                      <span className="badge border-amber-500/30 text-amber-300">sin guardar</span>
                    ) : w.last_save_ok ? (
                      <span className="badge border-emerald-500/30 text-emerald-300">OK</span>
                    ) : (
                      <span className="badge border-rose-500/30 text-rose-300">incompleto</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="mt-3 text-xs text-vh-muted">
          Un directorio 1.0 vacío es normal: el mundo aún no se ha guardado bajo
          el nuevo formato. Los ficheros legados <code>.db</code>/<code>.fwl</code>
          coexisten hasta la primera conversión.
        </div>
      </div>
    </div>
  );
}

function humanBytes(n: number): string {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(1)} ${u[i]}`;
}
