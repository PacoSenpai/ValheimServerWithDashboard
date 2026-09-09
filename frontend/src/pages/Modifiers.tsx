import { useEffect, useMemo, useState } from "react";
import { useApp } from "../lib/state";
import { api, type Modifiers } from "../lib/api";

const PRESETS = ["normal", "casual", "easy", "hard", "hardcore", "immersive", "hammer"];
const COMBAT = ["normal", "veryeasy", "easy", "hard", "veryhard"];
const DEATH = ["normal", "casual", "veryeasy", "easy", "hard", "hardcore"];
const RESOURCES = ["normal", "muchless", "less", "more", "muchmore", "most"];
const RAIDS = ["normal", "none", "muchless", "less", "more", "muchmore"];
const PORTALS = ["normal", "casual", "hard", "veryhard"];
const SETKEYS = ["nobuildcost", "playerevents", "passivemobs", "nomap"];

export function Modifiers() {
  const toast = useApp((s) => s.notify);
  const [m, setM] = useState<Modifiers | null>(null);
  const [diff, setDiff] = useState<Array<{ kind: string; arg: string }>>([]);
  const [pending, setPending] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.modifiers().then(setM).catch(() => {}); }, []);
  useEffect(() => {
    if (!m) return;
    api.previewModifiers(m).then((r) => {
      setDiff(r.diff);
      setPending(r.pending);
    }).catch((e) => toast("err", e?.message || String(e)));
  }, [m, toast]);

  const canApply = useMemo(() => m && m.preset !== undefined, [m]);

  if (!m) return <div className="card">Cargando…</div>;

  function update<K extends keyof Modifiers>(key: K, value: Modifiers[K]) {
    setM((cur) => (cur ? { ...cur, [key]: value } : cur));
  }

  function toggleKey(k: string) {
    if (!m) return;
    setM({ ...m, setkeys: m.setkeys.includes(k) ? m.setkeys.filter((x) => x !== k) : [...m.setkeys, k] });
  }

  async function apply() {
    if (!m) return;
    setBusy(true);
    try {
      await api.applyModifiers(m);
      toast("ok", "Modificadores aplicados. Reinicio en 30s.");
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Modificadores de mundo</h1>
      <div className="card space-y-3">
        <div>
          <label className="label">Preset (pisa modificadores anteriores)</label>
          <select className="select" value={m.preset}
            onChange={(e) => update("preset", e.target.value)}>
            {PRESETS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {([
            ["combat", COMBAT],
            ["deathpenalty", DEATH],
            ["resources", RESOURCES],
            ["raids", RAIDS],
            ["portals", PORTALS],
          ] as const).map(([k, opts]) => (
            <div key={k}>
              <label className="label">{k}</label>
              <select className="select" value={(m as any)[k]}
                onChange={(e) => update(k as any, e.target.value as any)}>
                {opts.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
        <div>
          <label className="label">Toggles (-setkey)</label>
          <div className="flex flex-wrap gap-2">
            {SETKEYS.map((k) => (
              <button
                key={k}
                className={`btn ${m.setkeys.includes(k) ? "btn-primary" : ""}`}
                onClick={() => toggleKey(k)}
              >
                {k}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Diff respecto a la config activa</div>
          <div className="text-xs text-vh-muted">Orden: -preset → -modifier → -setkey</div>
        </div>
        <div className="mt-2 max-h-64 overflow-y-auto rounded-md bg-vh-bg p-3 text-xs scrollbar-thin">
          {diff.length === 0 ? (
            <div className="text-vh-muted">Sin cambios.</div>
          ) : (
            diff.map((d, i) => (
              <div key={i} className={d.kind === "add" ? "text-emerald-300" : "text-rose-300"}>
                {d.kind === "add" ? "+ " : "- "} {d.arg}
              </div>
            ))
          )}
        </div>
        <pre className="mt-3 max-h-32 overflow-y-auto rounded-md bg-vh-bg p-2 text-[11px] leading-relaxed scrollbar-thin text-vh-muted">
          {pending.join(" ")}
        </pre>
      </div>
      <div className="flex gap-2">
        <button className="btn btn-primary" disabled={busy || !canApply} onClick={apply}>
          Aplicar y reiniciar (aviso 30s)
        </button>
      </div>
    </div>
  );
}
