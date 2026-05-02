#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/logs"
PIDS_FILE="$SCRIPT_DIR/.pids"
PORT="${PORT:-8001}"

mkdir -p "$LOG_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[ERROR] Missing virtualenv at $VENV_DIR"
  echo "Run ./deploy.sh first."
  exit 1
fi

# Stop previous local processes (if any)
pkill -f "uvicorn main:app --host 0.0.0.0 --port $PORT" 2>/dev/null || true
pkill -f "celery -A tasks.celery_app:celery_app worker" 2>/dev/null || true
pkill -f "celery -A tasks.celery_app beat" 2>/dev/null || true
sleep 1

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

echo "[OK] Backend: http://localhost:$PORT (PID $BACKEND_PID)"
echo "[OK] Worker PID: $WORKER_PID"
echo "[OK] Beat PID: $BEAT_PID"
echo "[OK] Logs in: $LOG_DIR"
