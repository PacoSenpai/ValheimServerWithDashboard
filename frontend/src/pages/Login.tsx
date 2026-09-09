import { useState } from "react";
import { useApp } from "../lib/state";
import { useNavigate } from "react-router-dom";

export function Login() {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useApp((s) => s.login);
  const toast = useApp((s) => s.notify);
  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.message || "Error de acceso");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid h-full place-items-center bg-vh-bg p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm card space-y-4"
      >
        <div>
          <div className="text-lg font-semibold">Valheim Dashboard</div>
          <div className="text-xs text-vh-muted">Acceso solo desde la LAN</div>
        </div>
        <div>
          <label className="label" htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            required
          />
        </div>
        {error ? <div className="text-sm text-rose-400">{error}</div> : null}
        <button
          type="submit"
          className="btn btn-primary w-full"
          disabled={busy || !password}
        >
          {busy ? "Accediendo…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
