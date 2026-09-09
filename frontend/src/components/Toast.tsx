import { useApp } from "../lib/state";
import clsx from "clsx";

export function Toast() {
  const toast = useApp((s) => s.toastMsg);
  if (!toast) return null;
  return (
    <div
      className={clsx(
        "fixed bottom-4 right-4 z-50 max-w-sm rounded-md border bg-vh-panel px-4 py-2 text-sm shadow-lg",
        toast.kind === "ok" && "border-emerald-500/40",
        toast.kind === "warn" && "border-yellow-500/40",
        toast.kind === "err" && "border-rose-500/60 text-rose-200",
      )}
    >
      {toast.text}
    </div>
  );
}
