import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { api } from "../lib/api";

const FILE_LABELS: Record<string, string> = {
  "adminlist.txt": "adminlist.txt — administradores",
  "bannedlist.txt": "bannedlist.txt — baneados",
  "permittedlist.txt": "permittedlist.txt — whitelist (vacía = servidor abierto)",
};

export function Lists() {
  const toast = useApp((s) => s.notify);
  const [data, setData] = useState<Record<string, string[]>>({});
  const [text, setText] = useState<Record<string, string>>({});
  const [crossplay, setCrossplay] = useState(false);

  async function load() {
    const d = await api.lists();
    setData(d);
    const t: Record<string, string> = {};
    for (const k of Object.keys(d)) t[k] = d[k].join("\n");
    setText(t);
  }
  useEffect(() => { load().catch((e) => toast("err", e?.message || String(e))); }, [toast]);

  async function save(name: string) {
    const entries = (text[name] || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
    try {
      const r = await api.saveList(name, entries);
      await load();
      toast("ok", `${name}: ${r.count} guardados${r.invalid.length ? `, ${r.invalid.length} inválidos` : ""}`);
    } catch (e: any) {
      toast("err", e?.message || String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Listas</h1>
      <div className="card text-xs text-vh-muted space-y-1">
        <p>
          IDs en <strong>modo Steam</strong>: <code>SteamID64</code> de 17 dígitos. En
          <strong> crossplay</strong>: <code>[Plataforma]_[UserID]</code> (case-sensitive).
        </p>
        <p>
          Admin ≠ cheats. Para comandos de trucos en un servidor dedicado necesitas el mod
          <em> Server Devcommands</em>, no incluido en la v1.
        </p>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={crossplay} onChange={(e) => setCrossplay(e.target.checked)} />
          Validar en formato crossplay
        </label>
      </div>
      {Object.entries(FILE_LABELS).map(([name, label]) => (
        <div key={name} className="card space-y-2">
          <div className="text-sm font-semibold">{label}</div>
          <textarea
            className="textarea h-40 font-mono text-xs"
            value={text[name] || ""}
            onChange={(e) => setText({ ...text, [name]: e.target.value })}
            placeholder="Un ID por línea"
          />
          <div className="flex justify-end gap-2">
            <button className="btn" onClick={() => save(name)}>Guardar</button>
          </div>
        </div>
      ))}
    </div>
  );
}
