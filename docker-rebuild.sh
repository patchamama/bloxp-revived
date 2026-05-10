#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/backend/.venv"
PIDS_FILE="$SCRIPT_DIR/.pids"

# Stop local mode processes (local mode cleanup)
echo "Stopping local backend/worker/beat processes..."
pkill -f "$VENV_DIR/bin/python -m uvicorn" 2>/dev/null || true
pkill -f "$VENV_DIR/bin/python -m celery" 2>/dev/null || true
if [ -f "$PIDS_FILE" ]; then
  while IFS='=' read -r _ pid; do
    kill "$pid" 2>/dev/null || true
  done < "$PIDS_FILE"
  rm -f "$PIDS_FILE"
fi
sleep 1

# Stop systemd services that conflict with docker-compose ports
for SVC in redis-server redis; do
  if systemctl is-active --quiet "$SVC" 2>/dev/null; then
    echo "Stopping systemd service: $SVC..."
    systemctl stop "$SVC" 2>/dev/null || true
  fi
done

# Free any remaining processes on ports declared in docker-compose.yml
PORTS=$(grep -E '^\s+- "[0-9]+:[0-9]+"' "$SCRIPT_DIR/docker-compose.yml" | sed 's/.*"\([0-9]*\):[0-9]*/\1/')
for PORT in $PORTS; do
  if fuser "$PORT/tcp" >/dev/null 2>&1; then
    echo "Freeing port $PORT..."
    fuser -k "$PORT/tcp" 2>/dev/null || true
    sleep 0.5
  fi
done

# Tear down existing containers so network/config changes take effect
echo "Tearing down existing containers..."
docker compose down 2>/dev/null || true

docker compose build backend worker
docker compose up -d backend worker beat
