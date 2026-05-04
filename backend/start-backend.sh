#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
PORT="${PORT:-8001}"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
WORKER_LOG="$LOG_DIR/worker.log"
BEAT_LOG="$LOG_DIR/beat.log"
NO_DOCKER_CHECK=false

for arg in "$@"; do
  case "$arg" in
    --no-docker-check) NO_DOCKER_CHECK=true ;;
    *)
      echo "[ERROR] Unknown argument: $arg"
      echo "Usage: bash start-backend.sh [--no-docker-check]"
      exit 1
      ;;
  esac
done

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[ERROR] Missing virtualenv at $VENV_DIR"
  exit 1
fi
if ! "$VENV_DIR/bin/python" -m celery --version >/dev/null 2>&1; then
  echo "[ERROR] celery is not available in $VENV_DIR"
  exit 1
fi

if [ "$NO_DOCKER_CHECK" = false ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[ERROR] Docker is not installed or not in PATH."
    echo "Install Docker Desktop/Engine and try again."
    echo "Or run bash start-backend.sh --no-docker-check if Redis is already available."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker daemon is not running."
    echo "Start Docker and try again."
    echo "Or run bash start-backend.sh --no-docker-check if Redis is already available."
    exit 1
  fi

  echo "[INFO] Ensuring Redis container is up (docker compose)..."
  cd "$ROOT_DIR"
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

mkdir -p "$LOG_DIR"
cd "$SCRIPT_DIR"

if ! pgrep -f "$VENV_DIR/bin/python -m celery -A tasks.celery_app:celery_app worker" >/dev/null 2>&1; then
  echo "[INFO] Celery worker not running, starting it..."
  nohup "$VENV_DIR/bin/python" -m celery -A tasks.celery_app:celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    > "$WORKER_LOG" 2>&1 &
fi
if ! pgrep -f "$VENV_DIR/bin/python -m celery -A tasks.celery_app beat" >/dev/null 2>&1; then
  echo "[INFO] Celery beat not running, starting it..."
  nohup "$VENV_DIR/bin/python" -m celery -A tasks.celery_app beat \
    --loglevel=info \
    > "$BEAT_LOG" 2>&1 &
fi

exec "$VENV_DIR/bin/python" -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
