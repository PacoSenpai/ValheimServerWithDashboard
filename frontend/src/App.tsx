import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useApp } from "./lib/state";
import { useLive } from "./lib/ws";
import { api } from "./lib/api";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Console } from "./pages/Console";
import { Config } from "./pages/Config";
import { Modifiers } from "./pages/Modifiers";
import { Worlds } from "./pages/Worlds";
import { Lists } from "./pages/Lists";
import { Backups } from "./pages/Backups";
import { Updates } from "./pages/Updates";
import { Schedule } from "./pages/Schedule";
import { Metrics } from "./pages/Metrics";
import { Notifications } from "./pages/Notifications";
import { Settings } from "./pages/Settings";
import { Toast } from "./components/Toast";

export default function App() {
  const authed = useApp((s) => s.authed);
  const refresh = useApp((s) => s.refresh);
  const setStatus = useApp((s) => s.setStatus);
  const pushMetric = useApp((s) => s.pushMetric);
  const setRoster = useApp((s) => s.setRoster);
  const setA2s = useApp((s) => s.setA2s);
  const navigate = useNavigate();
  const { messages, connected } = useLive();

  useEffect(() => {
    if (authed) {
      apiMe();
      const id = setInterval(refresh, 5000);
      return () => clearInterval(id);
    }
  }, [authed, refresh]);

  useEffect(() => {
    for (const m of messages) {
      if (m.topic === "metrics") pushMetric(m.payload);
      if (m.topic === "roster") setRoster(m.payload);
      if (m.topic === "a2s") setA2s(m.payload);
    }
  }, [messages, pushMetric, setRoster, setA2s]);

  useEffect(() => {
    if (!authed && location.pathname !== "/login") {
      navigate("/login", { replace: true });
    }
  }, [authed, navigate]);

  async function apiMe() {
    try {
      await api.me();
      useApp.setState({ authed: true });
      await refresh();
    } catch {
      useApp.setState({ authed: false });
    }
  }

  if (!authed) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <>
      <Layout connected={connected}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/console" element={<Console />} />
          <Route path="/config" element={<Config />} />
          <Route path="/modifiers" element={<Modifiers />} />
          <Route path="/worlds" element={<Worlds />} />
          <Route path="/lists" element={<Lists />} />
          <Route path="/backups" element={<Backups />} />
          <Route path="/updates" element={<Updates />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
      <Toast />
    </>
  );
}
