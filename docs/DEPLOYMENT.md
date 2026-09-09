# Despliegue

## Requisitos

- LXC Ubuntu 24.04 (unprivileged), 4 cores / 4 GB RAM / 16 GB rootfs.
- Acceso SSH al LXC como `root` para la instalación inicial; a partir de ahí se
  entra como `valheim`.
- UDP 2456-2458 abiertos en el router hacia la IP del LXC (modo Steam) — en modo
  crossplay no hace falta.
- Un nombre DNS que apunte a la IP pública (DDNS).
- Token de un bot de Telegram añadido al grupo donde quieres recibir avisos, y su
  `chat_id`.

## Pasos

### 1. Instalar el panel en el LXC

```bash
ssh root@lxc
useradd -m -s /bin/bash valheim
sudo -iu valheim
git clone <repo> ~/valheim-dashboard
cd ~/valheim-dashboard
./scripts/install.sh
```

`install.sh` hace, de forma idempotente:

- `dpkg --add-architecture i386` + repo `multiverse`.
- `apt install -y lib32gcc-s1 libatomic1 steamcmd zstd jq`.
- Crea `/opt/valheim/server`, `/var/lib/valheim/{saves,backups}`, `/var/log/valheim`.
- Instala el servicio systemd y el sudoers reducido.
- Crea el venv del backend y compila el frontend (si tiene Node) o usa el `dist`
  que trae el repo.
- Primera instalación de `896660` con `steamcmd`.
- Verifica con `ldd valheim_server.x86_64`.

### 2. Configurar secretos

`/etc/valheim-dashboard/config.toml` (permisos 0600):

```toml
[panel]
admin_password_hash = "<bcrypt>"
jwt_secret = "<generado al instalar>"

[game]
name = "Mi Servidor"
world = "Mi Mundo"
password = "********"
port = 2456
public = true
crossplay = false
savedir = "/var/lib/valheim/saves"
save_interval = 1800

[modifiers]
preset = "normal"

[telegram]
token = "123456:AAA..."
chat_id = "-100xxxxxxxxxx"
events = ["down", "resources", "maintenance", "update", "backup"]
```

Sobrescribir el token por variable de entorno:

```bash
export VALHEIM_DASHBOARD_TELEGRAM_TOKEN=...
```

### 3. Arrancar y verificar

```bash
sudo systemctl enable --now valheim-server
sudo systemctl enable --now valheim-dashboard
sudo systemctl status valheim-server valheim-dashboard
```

Accede a `http://<ip-del-lxc>:8080` desde la LAN.

### 4. Comisionado de 1.0

`docs/WORLD_MODIFIERS.md` lista los pasos a ejecutar nada más arrancar la
primera vez para verificar argumentos, líneas de log y A2S con el build 1.0
real. Hasta que esa sección no esté rellena, el panel está en modo “experimental”.

## Actualizar el panel

Desde tu equipo:

```bash
./scripts/deploy.sh
```

(Compila el frontend, hace rsync al LXC y reinicia `valheim-dashboard`.)

## Apagado de emergencia

Si la web no responde, entra por SSH y:

```bash
valheimctl status
valheimctl start | stop | restart
```

`valheimctl` es un wrapper de `systemctl` con autenticación NOPASSWD.
