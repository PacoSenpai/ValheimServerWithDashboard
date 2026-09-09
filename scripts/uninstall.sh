#!/usr/bin/env bash
set -euo pipefail

# Desinstalador. NO toca el servidor de juego ni los saves, pero deja el LXC
# sin el panel.

if [[ $EUID -ne 0 ]]; then
  echo "Ejecuta como root: sudo $0"
  exit 1
fi

systemctl disable --now valheim-dashboard.service || true
rm -f /etc/systemd/system/valheim-dashboard.service
rm -f /etc/systemd/system/valheim-server.service
systemctl daemon-reload
rm -f /etc/sudoers.d/valheim
rm -f /etc/logrotate.d/valheim
rm -rf /opt/valheim-dashboard
rm -rf /etc/valheim-dashboard
echo "Panel desinstalado. /opt/valheim (juego) y /var/lib/valheim (saves) se conservan."
