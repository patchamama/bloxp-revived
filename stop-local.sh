#!/usr/bin/env bash
# =============================================================================
# stop-local.sh — Stop all Bloxp Revived local services
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_FILE="$SCRIPT_DIR/.pids"

echo -e "\n Stopping Bloxp Revived services...\n"

if [ -f "$PIDS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$PIDS_FILE"
  for var in BACKEND_PID WORKER_PID BEAT_PID; do
    PID="${!var:-}"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID"
      success "Stopped $var (PID $PID)"
    else
      info "$var not running"
    fi
  done
  rm -f "$PIDS_FILE"
else
  info "No .pids file found, attempting fallback pkill..."
  pkill -f "uvicorn main:app" 2>/dev/null && success "Stopped uvicorn" || true
  pkill -f "celery -A tasks.celery_app" 2>/dev/null && success "Stopped Celery" || true
fi

echo -e "\n${GREEN}All services stopped.${NC}\n"
