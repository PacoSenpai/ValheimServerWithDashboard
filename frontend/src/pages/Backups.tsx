import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api, type BackupInfo } from "../lib/api";

export function Backups() {
  const toast = useApp((s) => s.notify);
  const [items, setItems] = useState<BackupInfo[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() { setItems(await api.backups()); }
  useEffect(() => { load().catch(() => {}); }, []);

  async function manual() {
    setBusy(true);
    try {
      await api.createBackup("manual");
      await load();
      toast("ok", "Backup creado");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally { setBusy(false); }
  }

  async function restore(id: number) {
    if (!confirm(`Restaurar backup ${id}? El servidor se parará, se hará un snapshot de seguridad y se reiniciará.`)) return;
    setBusy(true);
    try {
      await api.restoreBackup(id);
      await load();
      toast("ok", "Restauración lanzada");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Backups</h1>
      <div className="card flex items-center justify-between">
        <div className="text-sm">
          Política: snapshot antes de actualizar o aplicar modificadores, más manual.
          Retención: <strong>2</strong> snapshots. Se incluyen mundos 1.0 y legados.
        </div>
        <button className="btn btn-primary" disabled={busy} onClick={manual}>
          Crear backup ahora
        </button>
      </div>
      <div className="card">
        <div className="text-sm font-semibold">Snapshots ({items.length})</div>
        {items.length === 0 ? (
          <div className="mt-2 text-xs text-vh-muted">Sin snapshots. El primero se crea al actualizar o aplicar modificadores.</div>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead className="text-left text-xs uppercase text-vh-muted">
              <tr>
                <th className="py-1">#</th>
                <th>Fecha</th>
                <th>Motivo</th>
                <th>Tamaño</th>
                <th>Mundos</th>
                <th>sha256</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((b) => (
                <tr key={b.id} className="border-t border-vh-border">
                  <td className="py-1.5">{b.id}</td>
                  <td>{new Date(b.ts * 1000).toLocaleString()}</td>
                  <td>{b.reason}</td>
                  <td>{humanBytes(b.size_bytes)}</td>
                  <td className="text-xs">{b.worlds.join(", ") || "—"}</td>
                  <td className="font-mono text-[10px] text-vh-muted">{b.sha256.slice(0, 12)}…</td>
                  <td>
                    <button className="btn btn-danger" disabled={busy} onClick={() => restore(b.id)}>
                      Restaurar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
