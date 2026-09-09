import { useEffect, useRef, useState } from "react";
import { useConsole } from "../lib/ws";
import { api } from "../lib/api";

export function Console() {
  const [enabled, setEnabled] = useState(true);
  const { lines, connected } = useConsole(enabled);
  const ref = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState("");
  const [autoscroll, setAutoscroll] = useState(true);

  useEffect(() => {
    if (autoscroll && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines, autoscroll]);

  async function loadInitial() {
    try {
      const { lines: l } = await api.logsRecent(500);
      if (ref.current) {
        ref.current.dataset.prepend = l.join("\n");
        ref.current.scrollTop = ref.current.scrollHeight;
      }
    } catch {}
  }

  useEffect(() => { loadInitial(); }, []);

  const filtered = filter
    ? lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="input max-w-xs"
          placeholder="Filtrar…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <label className="flex items-center gap-2 text-xs text-vh-muted">
          <input
            type="checkbox"
            checked={autoscroll}
            onChange={(e) => setAutoscroll(e.target.checked)}
          />
          Auto-scroll
        </label>
        <span className={`badge ${connected ? "border-emerald-500/30 text-emerald-300" : "border-rose-500/30 text-rose-300"}`}>
          {connected ? "conectado" : "desconectado"}
        </span>
        <span className="ml-auto text-xs text-vh-muted">{filtered.length} líneas</span>
      </div>
      <div
        ref={ref}
        className="card scrollbar-thin h-[calc(100vh-180px)] overflow-y-auto p-2"
      >
        {filtered.map((l, i) => (
          <div
            key={i}
            className={`console-line px-1 ${colorize(l)}`}
          >
            {l}
          </div>
        ))}
        {filtered.length === 0 ? (
          <div className="p-4 text-xs text-vh-muted">Sin líneas. Activa el servidor o quita el filtro.</div>
        ) : null}
      </div>
    </div>
  );
}

function colorize(line: string): string {
  if (line.includes("Failed to authenticate") || line.includes("wrong password"))
    return "text-rose-400";
  if (line.includes("DungeonDB Start") || line.includes("Game server connected"))
    return "text-emerald-300";
  if (line.includes("join code"))
    return "text-amber-200";
  if (line.includes("ZDOID"))
    return "text-sky-300";
  if (line.includes("Closing socket"))
    return "text-slate-400";
  if (line.includes("Error") || line.includes("error"))
    return "text-rose-300";
  return "text-slate-200";
}
