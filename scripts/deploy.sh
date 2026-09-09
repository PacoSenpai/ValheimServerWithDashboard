#!/usr/bin/env bash
set -euo pipefail

# Compila el frontend y lo sincroniza al LXC destino.

VH_HOST=${VH_HOST:-}
VH_USER=${VH_USER:-valheim}
VH_PATH=${VH_PATH:-/home/valheim/valheim-dashboard}

if [[ -z "$VH_HOST" ]]; then
  echo "Define VH_HOST=ip-o-hostname del LXC. Ej: VH_HOST=192.168.1.50 $0"
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "==> Compilando frontend"
(cd "$ROOT_DIR/frontend" && npm install --no-audit --no-fund && npm run build)

echo "==> Sincronizando backend"
rsync -avz --delete \
  --exclude ".venv" --exclude "__pycache__" --exclude "*.pyc" \
  --exclude "data" \
  "$ROOT_DIR/backend/" "$VH_USER@$VH_HOST:$VH_PATH/backend/"

echo "==> Sincronizando frontend/dist"
rsync -avz --delete \
  "$ROOT_DIR/frontend/dist/" "$VH_USER@$VH_HOST:$VH_PATH/frontend/dist/"

echo "==> Reiniciando servicio"
ssh "$VH_USER@$VH_HOST" -- sudo systemctl restart valheim-dashboard.service
ssh "$VH_USER@$VH_HOST" -- sudo systemctl status valheim-dashboard.service --no-pager || true
