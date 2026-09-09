import { useEffect, useState } from "react";
import { useApp } from "../lib/state";
import { Stat } from "../components/Stat";
import { ServerBadge } from "../components/ServerBadge";
import { api, type NetworkInfo, type StatusPayload } from "../lib/api";

export function Dashboard() {
  const status = useApp((s) => s.status);
  const roster = useApp((s) => s.roster);
  const a2s = useApp((s) => s.a2s);
  const refresh = useApp((s) => s.refresh);
  const toast = useApp((s) => s.notify);
  const [network, setNetwork] = useState<NetworkInfo | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api.network().then(setNetwork).catch(() => {});
  }, [status?.server_state]);

  async function act(fn: () => Promise<any>, label: string) {
    setBusy(label);
    try {
      await fn();
      toast("ok", label);
      await refresh();
    } catch (e: any) {
      toast("err", e?.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  if (!status) {
    return <div className="card">Cargando…</div>;
  }

  const mode: "steam" | "crossplay" = status.server_state === "running" ? "steam" : "steam";
  void mode;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <div className="text-xs text-vh-muted">
            {status.version && <>v{status.version} · </>}
            {a2s?.name ? `${a2s.name}` : "A2S sin respuesta"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ServerBadge state={status.server_state} />
          <button
            className="btn"
            disabled={busy !== null}
            onClick={() => act(() => api.start(), "Arrancado")}
          >
            Arrancar
          </button>
          <button
            className="btn"
            disabled={busy !== null}
            onClick={() => act(() => api.restart(15, "manual"), "Reiniciando en 15s")}
          >
            Reiniciar (15s)
          </button>
          <button
            className="btn btn-danger"
            disabled={busy !== null}
            onClick={() => act(() => api.stop(), "Detenido")}
          >
            Detener
          </button>
        </div>
      </div>

      <ConnectionCard status={status} network={network} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label="Jugadores"
          value={roster?.count ?? a2s?.players ?? 0}
          hint={a2s?.max_players ? `Máx ${a2s.max_players}` : undefined}
        />
        <Stat label="Versión" value={status.version || "?"} />
        <Stat
          label="CPU host"
          value={`${status.metrics?.sys_cpu?.toFixed(0) ?? 0}%`}
          warn={(status.metrics?.sys_cpu ?? 0) > 80}
          danger={(status.metrics?.sys_cpu ?? 0) > 95}
        />
        <Stat
          label="RAM host"
          value={`${status.metrics?.sys_mem?.toFixed(0) ?? 0}%`}
          warn={(status.metrics?.sys_mem ?? 0) > 80}
          danger={(status.metrics?.sys_mem ?? 0) > 92}
        />
        <Stat
          label="Disco"
          value={`${status.metrics?.disk_pct?.toFixed(0) ?? 0}%`}
          warn={(status.metrics?.disk_pct ?? 0) > 80}
          danger={(status.metrics?.disk_pct ?? 0) > 92}
        />
        <Stat
          label="CPU proceso"
          value={`${status.metrics?.cpu?.toFixed(0) ?? 0}%`}
        />
        <Stat
          label="RSS"
          value={formatBytes(status.metrics?.rss ?? 0)}
        />
        <Stat
          label="Uptime"
          value={status.metrics ? `${Math.round((Date.now() / 1000 - status.metrics.ts))}s` : "—"}
        />
      </div>

      <RosterCard />
    </div>
  );
}

function ConnectionCard({ status, network }: { status: StatusPayload; network: NetworkInfo | null }) {
  const crossplay = useCrossplay(status);
  const host = network?.public_host || "(sin dominio configurado)";
  return (
    <div className="card space-y-2">
      <div className="text-sm font-semibold">Cómo unirse al servidor</div>
      {crossplay ? (
        <div>
          <div className="text-xs text-vh-muted">Modo crossplay — comparte este código con jugadores de consola</div>
          <div className="mt-2 flex items-center gap-3">
            <div className="rounded-md border border-vh-accent bg-vh-accent/10 px-4 py-2 font-mono text-2xl tracking-widest text-vh-accent">
              {status.join_code || rosterJoinCode() || "—"}
            </div>
            <div className="text-xs text-vh-muted">
              Steam puede usar también Join IP con el dominio.
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-1 text-sm">
          <div>
            Join IP (Steam):{" "}
            <code className="kbd">{host}:{network?.join_ip_url?.split(":").pop() || 2456}</code>
          </div>
          <div>
            Favoritos Steam:{" "}
            <code className="kbd">{host}:{network?.steam_favorites_url?.split(":").pop() || 2457}</code>
          </div>
          <div className="text-xs text-vh-muted">
            Asegúrate de tener UDP 2456–2458 abiertos en el router hacia el LXC.
          </div>
        </div>
      )}
    </div>
  );
}

function useCrossplay(status: StatusPayload): boolean {
  return Boolean(status?.server?.state && (status as any).crossplay);
}

function rosterJoinCode(): string | undefined {
  const r = useApp.getState().roster;
  return r?.join_code;
}

function RosterCard() {
  const roster = useApp((s) => s.roster);
  if (!roster?.online?.length) {
    return (
      <div className="card">
        <div className="text-sm font-semibold">Jugadores</div>
        <div className="mt-1 text-xs text-vh-muted">Nadie conectado ahora mismo.</div>
      </div>
    );
  }
  return (
    <div className="card">
      <div className="text-sm font-semibold">Jugadores en línea ({roster.count})</div>
      <ul className="mt-2 space-y-1 text-sm">
        {roster.online.map((p) => (
          <li key={p.steam_id} className="flex justify-between">
            <span>{p.name || p.steam_id.slice(-6)}</span>
            <span className="text-vh-muted">
              desde {new Date(p.joined_at * 1000).toLocaleTimeString()}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatBytes(n: number): string {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(0)} ${u[i]}`;
}
