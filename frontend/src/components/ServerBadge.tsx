import clsx from "clsx";

const LABELS: Record<string, { text: string; cls: string }> = {
  running: { text: "En marcha", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  starting: { text: "Arrancando", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  stopping: { text: "Parando", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  stopped: { text: "Detenido", cls: "bg-slate-500/15 text-slate-300 border-slate-500/30" },
  crashed: { text: "Caído", cls: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
  unknown: { text: "Desconocido", cls: "bg-slate-500/15 text-slate-300 border-slate-500/30" },
};

export function ServerBadge({ state }: { state: string }) {
  const l = LABELS[state] || LABELS.unknown;
  return <span className={clsx("badge", l.cls)}>{l.text}</span>;
}
