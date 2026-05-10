#!/usr/bin/env bash

# docker compose build backend worker && docker compose up -d backend worker beat

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/logs"
PIDS_FILE="$SCRIPT_DIR/.pids"
PORT="${PORT:-8001}"
BACKEND_URL_127="http://127.0.0.1:${PORT}/api/health"
BACKEND_URL_LOCALHOST="http://localhost:${PORT}/api/health"
NO_DOCKER_CHECK=false

for arg in "$@"; do
  case "$arg" in
    --no-docker-check|--local) NO_DOCKER_CHECK=true ;;
    *)
      echo "[ERROR] Unknown argument: $arg"
      echo "Usage: ./start-local.sh [--no-docker-check|--local]"
      exit 1
      ;;
  esac
done

free_compose_ports() {
  # Stop systemd services that conflict with docker-compose ports
  for SVC in redis-server redis; do
    if systemctl is-active --quiet "$SVC" 2>/dev/null; then
      echo "[INFO] Stopping systemd service: $SVC..."
      systemctl stop "$SVC" 2>/dev/null || true
    fi
  done

  local compose_file="$SCRIPT_DIR/docker-compose.yml"
  [ -f "$compose_file" ] || return 0
  local ports
  ports=$(grep -E '^\s+- "[0-9]+:[0-9]+"' "$compose_file" | sed 's/.*"\([0-9]*\):[0-9]*/\1/')
  for PORT_NUM in $ports; do
    if fuser "$PORT_NUM/tcp" >/dev/null 2>&1; then
      echo "[INFO] Freeing port $PORT_NUM..."
      fuser -k "$PORT_NUM/tcp" 2>/dev/null || true
      sleep 0.5
    fi
  done
}

mkdir -p "$LOG_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[ERROR] Missing virtualenv at $VENV_DIR"
  echo "Run ./deploy.sh first."
  exit 1
fi
if ! "$VENV_DIR/bin/python" -m uvicorn --version >/dev/null 2>&1; then
  echo "[ERROR] uvicorn is not available in $VENV_DIR"
  exit 1
fi
if ! "$VENV_DIR/bin/python" -m celery --version >/dev/null 2>&1; then
  echo "[ERROR] celery is not available in $VENV_DIR"
  exit 1
fi

_redis_reachable() {
  "$VENV_DIR/bin/python" -c "
import socket, sys
try:
    s = socket.create_connection(('127.0.0.1', 6379), timeout=1)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

USE_DOCKER_REDIS=false

if [ "$NO_DOCKER_CHECK" = false ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  USE_DOCKER_REDIS=true
fi

if [ "$USE_DOCKER_REDIS" = true ]; then
  echo "[INFO] Docker available — using Docker Redis."

  echo "[INFO] Freeing ports declared in docker-compose.yml..."
  free_compose_ports

  echo "[INFO] Stopping Docker backend/worker/beat (docker mode cleanup)..."
  docker compose stop backend worker beat 2>/dev/null || true
  docker compose rm -f backend worker beat 2>/dev/null || true

  echo "[INFO] Ensuring Redis container is up (docker compose)..."
  docker compose up -d redis >/dev/null
  REDIS_CID="$(docker compose ps -q redis)"
  if [ -z "$REDIS_CID" ]; then
    echo "[ERROR] Could not resolve redis container id from docker compose."
    exit 1
  fi

  REDIS_READY=false
  for _ in {1..30}; do
    REDIS_HEALTH="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$REDIS_CID" 2>/dev/null || true)"
    if [ "$REDIS_HEALTH" = "healthy" ] || [ "$REDIS_HEALTH" = "running" ]; then
      REDIS_READY=true
      break
    fi
    sleep 1
  done
  if [ "$REDIS_READY" = false ]; then
    echo "[ERROR] Redis container is not ready. Current status: ${REDIS_HEALTH:-unknown}"
    docker compose logs --no-color --tail 60 redis || true
    exit 1
  fi
else
  echo "[INFO] Docker not available or --local flag used — using system Redis."

  # Try to start Redis via systemd if not already running
  if ! _redis_reachable; then
    for SVC in redis redis-server; do
      if systemctl list-units --type=service --all 2>/dev/null | grep -q "${SVC}.service"; then
        echo "[INFO] Starting systemd service: $SVC..."
        systemctl start "$SVC" 2>/dev/null || true
        sleep 1
        break
      fi
    done
  fi

  # If still not reachable, try starting redis-server directly
  if ! _redis_reachable; then
    if command -v redis-server >/dev/null 2>&1; then
      echo "[INFO] Starting redis-server directly..."
      nohup redis-server --daemonize yes --logfile "$LOG_DIR/redis.log" >/dev/null 2>&1 || true
      sleep 2
    fi
  fi

  if ! _redis_reachable; then
    echo "[ERROR] Redis is not available on 127.0.0.1:6379."
    echo "Install Redis: apt install redis-server  OR  brew install redis"
    echo "Then run ./start-local.sh --local"
    exit 1
  fi

  echo "[INFO] Redis reachable at 127.0.0.1:6379."
fi

# Ensure Playwright Chromium binary is present in venv
if "$VENV_DIR/bin/python" -c "import playwright" >/dev/null 2>&1; then
  "$VENV_DIR/bin/python" -m playwright install chromium >/dev/null 2>&1 \
    || echo "[WARN] Playwright browser install failed — Wix browser discovery may be disabled"
else
  echo "[WARN] Playwright not in venv — run deploy.sh to enable Wix browser discovery"
fi

# Stop previous local processes (if any)
pkill -f "$VENV_DIR/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT" 2>/dev/null || true
pkill -f "$VENV_DIR/bin/python -m celery -A tasks.celery_app:celery_app worker" 2>/dev/null || true
pkill -f "$VENV_DIR/bin/python -m celery -A tasks.celery_app beat" 2>/dev/null || true
sleep 1

if command -v ss >/dev/null 2>&1; then
  if ss -ltn "( sport = :$PORT )" 2>/dev/null | tail -n +2 | grep -q .; then
    echo "[ERROR] Port $PORT is already in use before startup."
    echo "Stop the conflicting process or run with another port, e.g. PORT=8002 ./start-local.sh"
    exit 1
  fi
fi

cd "$BACKEND_DIR"

nohup "$VENV_DIR/bin/python" -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

nohup "$VENV_DIR/bin/python" -m celery -A tasks.celery_app:celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!

nohup "$VENV_DIR/bin/python" -m celery -A tasks.celery_app beat \
  --loglevel=info \
  > "$LOG_DIR/beat.log" 2>&1 &
BEAT_PID=$!

cat > "$PIDS_FILE" <<EOF
BACKEND_PID=$BACKEND_PID
WORKER_PID=$WORKER_PID
BEAT_PID=$BEAT_PID
EOF

for proc in "$BACKEND_PID" "$WORKER_PID" "$BEAT_PID"; do
  if ! kill -0 "$proc" 2>/dev/null; then
    echo "[ERROR] Process PID $proc exited during startup."
    echo "[INFO] Last backend log lines:"
    tail -n 60 "$LOG_DIR/backend.log" 2>/dev/null || true
    echo "[INFO] Last worker log lines:"
    tail -n 60 "$LOG_DIR/worker.log" 2>/dev/null || true
    echo "[INFO] Last beat log lines:"
    tail -n 60 "$LOG_DIR/beat.log" 2>/dev/null || true
    exit 1
  fi
done

if command -v curl >/dev/null 2>&1; then
  HEALTH_OK=false
  for _ in {1..20}; do
    if curl --noproxy '*' -fsS "$BACKEND_URL_127" >/dev/null 2>&1 || \
       curl --noproxy '*' -fsS "$BACKEND_URL_LOCALHOST" >/dev/null 2>&1; then
      HEALTH_OK=true
      break
    fi
    sleep 0.5
  done
  if [ "$HEALTH_OK" = false ]; then
    echo "[ERROR] Backend did not become healthy at $BACKEND_URL_127 nor $BACKEND_URL_LOCALHOST"
    tail -n 80 "$LOG_DIR/backend.log" 2>/dev/null || true
    exit 1
  fi
fi

echo "[OK] Backend: http://localhost:$PORT (PID $BACKEND_PID)"
echo "[OK] Worker PID: $WORKER_PID"
echo "[OK] Beat PID: $BEAT_PID"
echo "[OK] Logs in: $LOG_DIR"
