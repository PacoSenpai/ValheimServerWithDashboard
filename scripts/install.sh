#!/usr/bin/env bash
set -euo pipefail

# Instalación idempotente del panel en un LXC Ubuntu 24.04 ya existente.
# Ejecutar como root una vez. NO crea el LXC.

if [[ $EUID -ne 0 ]]; then
  echo "Ejecuta como root: sudo $0"
  exit 1
fi

VH_USER=${VH_USER:-valheim}
VH_HOME="/home/$VH_USER"
DASH_ROOT="$VH_HOME/valheim-dashboard"
DASH_OPT="/opt/valheim-dashboard"
GAME_DIR="/opt/valheim"
CFG_DIR="/etc/valheim-dashboard"
LOG_DIR="/var/log/valheim"
SAVEDIR="/var/lib/valheim/saves"
BACKUPDIR="/var/lib/valheim/backups"

echo "==> Usuario $VH_USER"
if ! id "$VH_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$VH_USER"
fi

echo "==> Dependencias del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends software-properties-common ca-certificates curl gnupg
dpkg --add-architecture i386 >/dev/null
add-apt-repository -y multiverse >/dev/null
apt-get update
apt-get install -y --no-install-recommends \
  lib32gcc-s1 libatomic1 zstd jq ufw

if ! command -v steamcmd >/dev/null 2>&1; then
  echo "==> steamcmd: instalando desde el repo multiverse"
  apt-get install -y --no-install-recommends steamcmd || {
    echo "AVISO: 'apt install steamcmd' falló. Lo descargaremos manualmente."
    if ! id steam >/dev/null 2>&1; then
      useradd -m -s /bin/bash steam
    fi
    sudo -u steam -- bash -c '
      set -e
      mkdir -p /home/steam/steamcmd
      cd /home/steam/steamcmd
      curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
      ./steamcmd.sh +quit
    '
    ln -sf /home/steam/steamcmd/steamcmd.sh /usr/local/bin/steamcmd
  }
fi

echo "==> Estructura de directorios"
mkdir -p "$GAME_DIR" "$CFG_DIR" "$LOG_DIR" "$SAVEDIR" "$BACKUPDIR" \
         "/var/lib/valheim-dashboard"
chown -R "$VH_USER:$VH_USER" "$LOG_DIR" "$SAVEDIR" "$BACKUPDIR" \
                          "/var/lib/valheim-dashboard" "$GAME_DIR"

echo "==> Despliegue del código"
if [[ -d "$DASH_ROOT" ]]; then
  sudo -u "$VH_USER" -- bash -c "cd $DASH_ROOT && git pull --recurse-submodules"
else
  echo "ERROR: clona el repo en $DASH_ROOT antes de continuar."
  exit 1
fi

echo "==> Backend (venv + deps)"
sudo -u "$VH_USER" -- bash -c "
  set -e
  python3 -m venv $DASH_ROOT/backend/.venv
  $DASH_ROOT/backend/.venv/bin/python -m pip install --upgrade pip wheel
  $DASH_ROOT/backend/.venv/bin/python -m pip install -e $DASH_ROOT/backend
"

echo "==> Vinculando instalación"
ln -sfn "$DASH_ROOT/backend" "$DASH_OPT"

if [[ -d "$DASH_ROOT/frontend/dist" ]]; then
  mkdir -p "$DASH_OPT/frontend"
  ln -sfn "$DASH_ROOT/frontend/dist" "$DASH_OPT/frontend/dist"
elif command -v npm >/dev/null 2>&1; then
  echo "==> Construyendo frontend (npm install + build)..."
  sudo -u "$VH_USER" -- bash -c "
    set -e
    cd $DASH_ROOT/frontend
    npm install --no-audit --no-fund
    npm run build
  "
  if [[ -d "$DASH_ROOT/frontend/dist" ]]; then
    mkdir -p "$DASH_OPT/frontend"
    ln -sfn "$DASH_ROOT/frontend/dist" "$DASH_OPT/frontend/dist"
  else
    echo "AVISO: build del frontend falló. El panel seguirá siendo solo API."
  fi
else
  echo "AVISO: no hay frontend/dist y no hay npm. El panel seguirá siendo solo API."
fi

echo "==> Configuración inicial"
if [[ ! -f "$CFG_DIR/config.toml" ]]; then
  cp "$DASH_ROOT/deploy/config.toml.example" "$CFG_DIR/config.toml"
  SECRET_KEY=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 64)
  cat >> "$CFG_DIR/config.toml" <<EOF
# Secretos generados en $(date -Iseconds)
[panel]
secret_key_file = "$CFG_DIR/secret.key"
admin_password_hash_file = "$CFG_DIR/admin_password_hash"
EOF
  echo "$SECRET_KEY" > "$CFG_DIR/secret.key"
  INIT_PASSWORD=${INIT_PASSWORD:-$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)}
  $DASH_ROOT/backend/.venv/bin/python -c \
    "import bcrypt; open('$CFG_DIR/admin_password_hash','wb').write(bcrypt.hashpw(b'$INIT_PASSWORD', bcrypt.gensalt()))"
  echo
  echo "============================================================"
  echo "Password inicial del panel: $INIT_PASSWORD"
  echo "Cámbialo en cuanto puedas desde la UI (Ajustes)."
  echo "============================================================"
  echo
fi
chmod 0600 "$CFG_DIR/config.toml" "$CFG_DIR/secret.key" "$CFG_DIR/admin_password_hash" 2>/dev/null || true
chown -R "$VH_USER:$VH_USER" "$CFG_DIR"

echo "==> Sudoers reducido"
cp "$DASH_ROOT/deploy/sudoers-valheim" /etc/sudoers.d/valheim
chmod 0440 /etc/sudoers.d/valheim
visudo -c -f /etc/sudoers.d/valheim

echo "==> Servicios systemd"
cp "$DASH_ROOT/deploy/valheim-server.service" /etc/systemd/system/
cp "$DASH_ROOT/deploy/valheim-dashboard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable valheim-dashboard.service

echo "==> Logrotate"
cp "$DASH_ROOT/deploy/logrotate-valheim" /etc/logrotate.d/valheim

echo "==> UFW (ajusta el rango LAN a tu red)"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 8080/tcp
ufw allow 2456:2458/udp
ufw --force enable

echo "==> valheimctl"
install -m 0755 "$DASH_ROOT/scripts/valheimctl" /usr/local/bin/valheimctl

echo "==> Steamcmd (descarga inicial de 896660, si no existe)"
if [[ ! -f "$GAME_DIR/valheim_server.x86_64" ]]; then
  sudo -u "$VH_USER" -- bash -c "steamcmd +force_install_dir $GAME_DIR +login anonymous +app_update 896660 validate +quit" \
    || echo "AVISO: steamcmd falló. Reintenta con: sudo -u $VH_USER steamcmd +force_install_dir $GAME_DIR +login anonymous +app_update 896660 validate +quit"
fi

echo "==> Arrancando el panel"
systemctl restart valheim-dashboard.service
systemctl status valheim-dashboard.service --no-pager || true
echo
echo "Accede en http://<ip-del-lxc>:8080"
echo "  Usuario: admin"
echo "  Password: (la generada arriba, si no usaste INIT_PASSWORD=...)"
