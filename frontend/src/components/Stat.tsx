import clsx from "clsx";

export function Stat({
  label,
  value,
  hint,
  warn,
  danger,
}: {
  label: string;
  value: string | number;
  hint?: string;
  warn?: boolean;
  danger?: boolean;
}) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div
        className={clsx(
          "text-2xl font-semibold tracking-tight",
          danger ? "text-rose-400" : warn ? "text-amber-300" : "text-slate-100",
        )}
      >
        {value}
      </div>
      {hint ? <div className="mt-1 text-xs text-vh-muted">{hint}</div> : null}
    </div>
  );
}
