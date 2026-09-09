# Arquitectura

## Vista general

```
┌─ LXC Ubuntu 24.04 ───────────────────────────────────────────┐
│                                                               │
│  valheim-dashboard.service (FastAPI/uvicorn, user: valheim)  │
│    REST  /api/*      auth, config, mundos, listas, backups    │
│    WS    /ws/live    estado+jugadores+métricas (1 s)          │
│    WS    /ws/console líneas de log en vivo                    │
│    Scheduler (APScheduler): reinicios, idle-shutdown,         │
│              retención métricas, chequeo de updates           │
│    Notifier: Telegram (umbrales, cooldown, dedupe)            │
│    SQLite: métricas, sesiones, auditoría, jugadores, backups  │
│             │ sudoers NOPASSWD (systemctl start/stop/restart/ │
│             │  status/kill -s SIGINT valheim-server)         │
│             ▼                                                 │
│  valheim-server.service (user: valheim, Nice=-5)              │
│    ExecStart=valheim_server.x86_64 -nographics -batchmode …   │
│    EnvironmentFile=/etc/valheim-dashboard/valheim.env (ARGS)  │
│    StandardOutput=append:/var/log/valheim/server.log          │
│    KillSignal=SIGINT  TimeoutStopSec=120  Restart=on-failure  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
     ▲ UDP 2456-2458 (modo Steam)      ▲ A2S 2457/2458 (sondeo)
     │                                 └ tail -F server.log (parseo)
```

## Fuentes de verdad (en orden de preferencia)

1. **systemd / proceso** — el servidor está vivo o no, su PID, estado del unit.
2. **A2S query (UDP 2457/2458)** — nombre, jugadores, versión. Puede no responder
   en modo crossplay.
3. **Log parseado** — `tail -F` con reglas regex versionadas: `DungeonDB Start`,
   `Got character ZDOID from <name>`, `Closing socket <id>`, `join code (\w{6})`,
   `Failed to authenticate user`, etc. Es la fuente del roster con SteamID, muertes,
   join code, y de los avisos a jugadores que en vanilla no se pueden emitir
   in-game.

## Layout de ficheros en el LXC

```
/opt/valheim/server          # binarios del juego (steamcmd)
/var/lib/valheim/saves       # -savedir: worlds_local/, adminlist.txt, ...
/var/lib/valheim/backups     # snapshots (tar.zst, retención 2)
/var/log/valheim/server.log  # stdout/stderr del juego (+ logrotate)
/etc/valheim-dashboard/      # config.toml (secretos), valheim.env (ARGS)
/opt/valheim-dashboard/      # backend + frontend/dist
```

## Generación de argumentos

El módulo `app.services.args` produce el argv a partir de un modelo tipado
(`ServerConfig`, `WorldModifiers`). Reglas:

- Orden obligatorio: `-preset → -modifier → -setkey`. El preset pisa lo anterior.
- El modificador `normal` se omite (sin flag) en `-modifier`; cualquier otro valor
  se emite.
- `-setkey` se puede repetir y siempre va al final.
- Validación de password: ≥5 caracteres, sin `" @ !`, no contenido en el nombre
  del mundo, distinto del nombre del servidor.
- La UI muestra el argv resultante en vivo y el diff contra lo activo, y exige
  reinicio para aplicar.

La lista real de valores aceptados por la build 1.0 está pendiente de verificación
empírica (ver `docs/WORLD_MODIFIERS.md`).

## Persistencia

- **SQLite** en `data/app.sqlite` con `WAL`.
- **Métricas**: `metrics_samples` (1 s) → `metrics_5m` (downsample) → `metrics_1h`
  (downsample a 7 días). Retención por defecto 30 días.
- **Jugadores**: `players`, `player_sessions` (basado en eventos del parser).
- **Backups**: `backups` (id, ruta, tamaño, sha256, fecha, motivo).
- **Auditoría**: `audit_log` (actor, acción, payload, timestamp).

## Scheduler

APScheduler en proceso. Jobs:

- `metrics_sample` cada 1 s.
- `metrics_downsample` cada 5 min.
- `check_update` cada 6 h (configurable).
- `restart_scheduled` según tabla.
- `idle_off` cada 1 min (compara 0 jugadores durante N min).
- `backup_pre_*` antes de actualizaciones / cambios destructivos.

## Notificador Telegram

Cliente `httpx` async → `sendMessage` con `parse_mode=HTML`. Cola con rate limit
(1 msg/s, ≤20/min por chat) y 3 reintentos. Cooldown y dedupe por tipo de evento.
Un solo destino (`chat_id`).

Eventos activos por defecto:

- Caídas y reinicios.
- Alertas de recursos (CPU/RAM/disco) con recuperación.
- Avisos a jugadores (T-10 y T-1 min antes de reinicio; “modificadores aplicados”).
- Actualizaciones del juego.
- Backups OK/fallidos.

Implementados pero OFF: entradas/salidas, muertes, contraseñas erróneas.

## Seguridad

- Cookie de sesión `httpOnly` + `SameSite=Strict`, JWT firmado con clave generada
  en la primera instalación (`/etc/valheim-dashboard/secret.key`).
- `bcrypt` para el password del panel (un único usuario admin).
- Rate limit en `/api/auth/login` (5/min).
- UFW: solo UDP 2456-2458 y panel desde tu LAN.
- Sudoers reducido a los `systemctl` exactos.
- Token del bot de Telegram y claves nunca en el repo, en `config.toml` con `0600`
  y enmascarados en logs/UI.
- Auditoría: cada acción de cambio queda registrada.
