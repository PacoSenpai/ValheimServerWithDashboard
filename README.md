# ValheimServerWithDashboard

Panel de control para un servidor dedicado de **Valheim 1.0** sobre un LXC de Proxmox.
Incluye gestión de modificadores de mundo, reinicio con aviso, backups, actualizaciones
vía `steamcmd`, monitorización de jugadores y recursos en tiempo real, y avisos a un
grupo de Telegram.

## Stack

- **Servidor de juego**: nativo + `systemd` (AppID 896660).
- **Panel**: FastAPI (Python 3.12) + WebSockets; React 18 + TypeScript + Vite.
- **Persistencia**: SQLite (WAL) y ficheros en disco.
- **Despliegue**: LXC Ubuntu 24.04, unprivileged, `dpkg --add-architecture i386` + `steamcmd`.

## Estructura

```
backend/    API + servicios (FastAPI)
frontend/   SPA (Vite + React)
deploy/     unidades systemd, sudoers, logrotate, ufw
scripts/    install.sh, deploy.sh, valheimctl
tools/      fake-valheim-server.py, probes
docs/       ARCHITECTURE.md, DEPLOYMENT.md, WORLD_MODIFIERS.md, RUNBOOK.md
```

## Arranque rápido (desarrollo)

```bash
make install
make dev
```

`make dev` levanta backend y frontend, y conecta al servidor falso para que puedas
probar todo el panel sin instalar Valheim.

## Despliegue (LXC destino)

Ver [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Aviso

Valheim 1.0 sale el 9 de septiembre de 2026. Los modificadores de mundo y las
líneas de log se verifican empíricamente en la fase de comisionado y se documentan
en [`docs/WORLD_MODIFIERS.md`](docs/WORLD_MODIFIERS.md). La modificación de un
servidor en producción corre de tu cuenta.
