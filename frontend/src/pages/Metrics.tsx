import { useEffect, useMemo, useState } from "react";
import { useApp } from "../lib/state";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { api, type MetricSample } from "../lib/api";

export function Metrics() {
  const live = useApp((s) => s.metrics);
  const [history, setHistory] = useState<MetricSample[]>([]);

  useEffect(() => {
    api.metricsHistory(60).then(setHistory).catch(() => {});
  }, []);

  const data = useMemo(() => {
    const merged = [...history, ...live.filter((m) => !history.find((h) => h.ts === m.ts))];
    return merged.slice(-600).map((m) => ({
      t: new Date(m.ts * 1000).toLocaleTimeString().slice(0, 8),
      sys_cpu: m.sys_cpu,
      sys_mem: m.sys_mem,
      disk: m.disk_pct,
      proc_cpu: m.cpu,
      rss: m.rss / 1024 / 1024,
    }));
  }, [history, live]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Métricas (últimos 60 min)</h1>
      <div className="card">
        <div className="text-sm font-semibold mb-2">CPU y memoria del host</div>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={data}>
              <XAxis dataKey="t" minTickGap={40} tick={{ fill: "#8a93a4", fontSize: 11 }} />
              <YAxis tick={{ fill: "#8a93a4", fontSize: 11 }} domain={[0, 100]} unit="%" />
              <Tooltip
                contentStyle={{ background: "#161a22", border: "1px solid #262c38" }}
                labelStyle={{ color: "#8a93a4" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line dataKey="sys_cpu" name="CPU host %" dot={false} stroke="#e5b25d" strokeWidth={1.5} />
              <Line dataKey="sys_mem" name="RAM host %" dot={false} stroke="#7c9c5b" strokeWidth={1.5} />
              <Line dataKey="disk" name="Disco %" dot={false} stroke="#d96b6b" strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="card">
        <div className="text-sm font-semibold mb-2">Proceso Valheim</div>
        <div className="h-56">
          <ResponsiveContainer>
            <LineChart data={data}>
              <XAxis dataKey="t" minTickGap={40} tick={{ fill: "#8a93a4", fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fill: "#8a93a4", fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#8a93a4", fontSize: 11 }} unit=" MB" />
              <Tooltip
                contentStyle={{ background: "#161a22", border: "1px solid #262c38" }}
                labelStyle={{ color: "#8a93a4" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="left" dataKey="proc_cpu" name="CPU %" dot={false} stroke="#e5b25d" />
              <Line yAxisId="right" dataKey="rss" name="RSS (MB)" dot={false} stroke="#7c9c5b" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
