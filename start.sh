#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/logs"
PIDS_FILE="$SCRIPT_DIR/.pids"
PORT="${PORT:-8001}"
BACKEND_URL="http://127.0.0.1:${PORT}/api/health"
NO_DOCKER_CHECK=false

for arg in "$@"; do
  case "$arg" in
    --no-docker-check) NO_DOCKER_CHECK=true ;;
    *)
      echo "[ERROR] Unknown argument: $arg"
      echo "Usage: ./start.sh [--no-docker-check]"
      exit 1
      ;;
  esac
done

mkdir -p "$LOG_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[ERROR] Missing virtualenv at $VENV_DIR"
  echo "Run ./deploy.sh first."
  exit 1
fi
if [ ! -x "$VENV_DIR/bin/uvicorn" ]; then
  echo "[ERROR] Missing uvicorn at $VENV_DIR/bin/uvicorn"
  exit 1
fi
if [ ! -x "$VENV_DIR/bin/celery" ]; then
  echo "[ERROR] Missing celery at $VENV_DIR/bin/celery"
  exit 1
fi

if [ "$NO_DOCKER_CHECK" = false ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[ERROR] Docker is not installed or not in PATH."
    echo "Install Docker Desktop/Engine and try again."
    echo "Or run ./start.sh --no-docker-check if Redis is already available."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker daemon is not running."
    echo "Start Docker and try again."
    echo "Or run ./start.sh --no-docker-check if Redis is already available."
    exit 1
  fi

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
  echo "[INFO] Skipping Docker/Redis checks (--no-docker-check)."
fi

# Stop previous local processes (if any)
pkill -f "$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port $PORT" 2>/dev/null || true
pkill -f "$VENV_DIR/bin/celery -A tasks.celery_app:celery_app worker" 2>/dev/null || true
pkill -f "$VENV_DIR/bin/celery -A tasks.celery_app beat" 2>/dev/null || true
sleep 1

if command -v ss >/dev/null 2>&1; then
  if ss -ltn "( sport = :$PORT )" 2>/dev/null | tail -n +2 | grep -q .; then
    echo "[ERROR] Port $PORT is already in use before startup."
    echo "Stop the conflicting process or run with another port, e.g. PORT=8002 ./start.sh"
    exit 1
  fi
fi

cd "$BACKEND_DIR"

nohup "$VENV_DIR/bin/uvicorn" main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

nohup "$VENV_DIR/bin/celery" -A tasks.celery_app:celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!

nohup "$VENV_DIR/bin/celery" -A tasks.celery_app beat \
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
    if curl -fsS "$BACKEND_URL" >/dev/null 2>&1; then
      HEALTH_OK=true
      break
    fi
    sleep 0.5
  done
  if [ "$HEALTH_OK" = false ]; then
    echo "[ERROR] Backend did not become healthy at $BACKEND_URL"
    tail -n 80 "$LOG_DIR/backend.log" 2>/dev/null || true
    exit 1
  fi
fi

echo "[OK] Backend: http://localhost:$PORT (PID $BACKEND_PID)"
echo "[OK] Worker PID: $WORKER_PID"
echo "[OK] Beat PID: $BEAT_PID"
echo "[OK] Logs in: $LOG_DIR"
