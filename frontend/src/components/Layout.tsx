import { NavLink } from "react-router-dom";
import clsx from "clsx";

const NAV: Array<{ to: string; label: string }> = [
  { to: "/", label: "Dashboard" },
  { to: "/console", label: "Consola" },
  { to: "/modifiers", label: "Modificadores" },
  { to: "/config", label: "Configuración" },
  { to: "/worlds", label: "Mundos" },
  { to: "/lists", label: "Listas" },
  { to: "/backups", label: "Backups" },
  { to: "/updates", label: "Actualizaciones" },
  { to: "/schedule", label: "Programación" },
  { to: "/metrics", label: "Métricas" },
  { to: "/notifications", label: "Telegram" },
  { to: "/settings", label: "Ajustes" },
];

export function Layout({ children, connected }: { children: React.ReactNode; connected: boolean }) {
  return (
    <div className="flex h-full">
      <aside className="hidden md:flex w-60 flex-col border-r border-vh-border bg-vh-panel/60 p-3">
        <div className="mb-4 flex items-center gap-2">
          <span className="text-xl">⚔️</span>
          <span className="font-semibold tracking-wide">Valheim</span>
        </div>
        <nav className="flex flex-col gap-0.5">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                clsx(
                  "rounded-md px-3 py-1.5 text-sm transition",
                  isActive
                    ? "bg-vh-accent/15 text-vh-accent"
                    : "text-slate-300 hover:bg-vh-panel hover:text-slate-100",
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-2 text-[10px] text-vh-muted">
          <span className={clsx("mr-1 inline-block h-1.5 w-1.5 rounded-full", connected ? "bg-emerald-400" : "bg-rose-500")} />
          {connected ? "Tiempo real conectado" : "Sin conexión en vivo"}
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto scrollbar-thin p-4 md:p-6">
        <div className="md:hidden mb-3 flex flex-wrap gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                clsx(
                  "rounded-md border px-2 py-1 text-xs",
                  isActive
                    ? "border-vh-accent text-vh-accent"
                    : "border-vh-border text-slate-400",
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </div>
        {children}
      </main>
    </div>
  );
}
