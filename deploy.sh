#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Bloxp Revived local production deploy
#
# Builds the React frontend, copies the dist into the backend, sets up a
# Python virtual environment, installs all dependencies, and starts the
# FastAPI server + Celery worker ready for production use (no Docker needed).
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh              # full deploy
#   ./deploy.sh --no-build   # skip frontend build (re-use existing dist)
#   ./deploy.sh --no-venv    # skip venv creation (already exists)
#
# Requirements:
#   - Node.js >= 18 and npm
#   - Python >= 3.11
#   - Redis running on localhost:6379  (brew install redis && brew services start redis)
#   - Calibre (optional, for Mobi output)  (brew install --cask calibre)
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}▶  $*${NC}"; }

# ── Flags ─────────────────────────────────────────────────────────────────────
BUILD_FRONTEND=true
SETUP_VENV=true

for arg in "$@"; do
  case $arg in
    --no-build) BUILD_FRONTEND=false ;;
    --no-venv)  SETUP_VENV=false     ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \{0,2\}//'
      exit 0 ;;
  esac
done

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_DIR="$SCRIPT_DIR/backend"
STATIC_DIR="$BACKEND_DIR/static"
VENV_DIR="$BACKEND_DIR/.venv"
GENERATED_DIR="$SCRIPT_DIR/generated"
LOG_DIR="$SCRIPT_DIR/logs"

echo -e "\n${BOLD}╔══════════════════════════════════════╗"
echo -e "║   Bloxp Revived — Local Deploy       ║"
echo -e "╚══════════════════════════════════════╝${NC}\n"

# ── Detect OS ─────────────────────────────────────────────────────────────────
OS="$(uname -s)"

# ── 1. Prerequisites check ────────────────────────────────────────────────────
step "Checking prerequisites"

if [ "$OS" = "Linux" ]; then
  command -v node  >/dev/null 2>&1 || error "Node.js not found. Install via: sudo apt-get install -y nodejs npm"
  command -v npm   >/dev/null 2>&1 || error "npm not found. Install via: sudo apt-get install -y npm"
  command -v python3 >/dev/null 2>&1 || error "Python 3 not found. Install via: sudo apt-get install -y python3 python3-venv python3-pip"
else
  command -v node  >/dev/null 2>&1 || error "Node.js not found. Install via: brew install node"
  command -v npm   >/dev/null 2>&1 || error "npm not found."
  command -v python3 >/dev/null 2>&1 || error "Python 3 not found. Install via: brew install python"
fi

NODE_VER=$(node -v | sed 's/v//')
PY_VER=$(python3 --version | awk '{print $2}')
info "Node.js $NODE_VER | Python $PY_VER"

# ── Check / install / start Redis ─────────────────────────────────────────────
if ! redis-cli ping >/dev/null 2>&1; then
  warn "Redis is not running. Attempting to start..."
  if [ "$OS" = "Linux" ]; then
    if ! command -v redis-server >/dev/null 2>&1; then
      info "Installing Redis via apt..."
      sudo apt-get update -qq \
        && sudo apt-get install -y redis-server >/dev/null 2>&1 \
        || error "Could not install Redis. Run: sudo apt-get install redis-server"
    fi
    if command -v systemctl >/dev/null 2>&1; then
      sudo systemctl start redis-server 2>/dev/null \
        || sudo service redis-server start 2>/dev/null \
        || redis-server --daemonize yes 2>/dev/null \
        || error "Could not start Redis."
    else
      sudo service redis-server start 2>/dev/null \
        || redis-server --daemonize yes 2>/dev/null \
        || error "Could not start Redis."
    fi
  elif [ "$OS" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew services start redis >/dev/null 2>&1 \
        || error "Could not start Redis. Run: brew install redis && brew services start redis"
    else
      error "Redis is not running. Install: brew install redis && brew services start redis"
    fi
  else
    error "Redis is not running. Start it manually: redis-server"
  fi
  sleep 1
  redis-cli ping >/dev/null 2>&1 || error "Redis still unreachable after start attempt."
fi
success "Redis is running"

if command -v ebook-convert >/dev/null 2>&1; then
  success "Calibre found — Mobi output enabled"
else
  warn "Calibre not found — Mobi output will be disabled (ePub and PDF still work)"
fi

# ── 2. Build frontend ─────────────────────────────────────────────────────────
if [ "$BUILD_FRONTEND" = true ]; then
  step "Building React frontend"
  cd "$FRONTEND_DIR"

  info "Installing npm dependencies..."
  npm install --silent

  info "Running production build..."
  npm run build

  success "Frontend built → $FRONTEND_DIR/dist"
else
  info "Skipping frontend build (--no-build)"
  [ -d "$FRONTEND_DIR/dist" ] || error "No dist/ folder found. Run without --no-build first."
fi

# ── 3. Copy dist → backend/static ─────────────────────────────────────────────
step "Copying frontend dist to backend/static"
rm -rf "$STATIC_DIR"
cp -r "$FRONTEND_DIR/dist" "$STATIC_DIR"
success "Copied to $STATIC_DIR"

# ── 4. Python virtual environment ─────────────────────────────────────────────
step "Setting up Python virtual environment"
cd "$BACKEND_DIR"

if [ "$SETUP_VENV" = true ]; then
  if [ -d "$VENV_DIR" ]; then
    info "Virtual environment already exists, recreating..."
    rm -rf "$VENV_DIR"
  fi
  info "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  info "Skipping venv creation (--no-venv)"
  [ -d "$VENV_DIR" ] || error "No .venv found at $VENV_DIR. Run without --no-venv first."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

info "Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
success "Python dependencies installed"

# ── 5. Create required directories ────────────────────────────────────────────
step "Creating runtime directories"
mkdir -p "$GENERATED_DIR" "$LOG_DIR"
success "Directories ready: generated/ logs/"

# ── 6. Write .env if missing ──────────────────────────────────────────────────
ENV_FILE="$BACKEND_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  step "Creating default .env"
  cat > "$ENV_FILE" << 'EOF'
REDIS_URL=redis://localhost:6379/0
GENERATED_DIR=../generated
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
EOF
  success "Created $ENV_FILE — edit it to configure SMTP"
else
  info ".env already exists, skipping"
fi

# ── 7. Kill any previous processes ────────────────────────────────────────────
step "Stopping any previous Bloxp processes"
pkill -f "uvicorn main:app" 2>/dev/null && info "Stopped previous uvicorn" || true
pkill -f "celery -A tasks.celery_app worker" 2>/dev/null && info "Stopped previous Celery worker" || true
pkill -f "celery -A tasks.celery_app beat" 2>/dev/null && info "Stopped previous Celery beat" || true
sleep 1

# ── 8. Start services ─────────────────────────────────────────────────────────
step "Starting Bloxp services"
cd "$BACKEND_DIR"

# FastAPI
nohup "$VENV_DIR/bin/uvicorn" main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
success "Backend started (PID $BACKEND_PID) → http://localhost:8000"

# Celery worker
nohup "$VENV_DIR/bin/celery" -A tasks.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  > "$LOG_DIR/worker.log" 2>&1 &
WORKER_PID=$!
success "Celery worker started (PID $WORKER_PID)"

# Celery beat (cleanup scheduler)
nohup "$VENV_DIR/bin/celery" -A tasks.celery_app beat \
  --loglevel=info \
  > "$LOG_DIR/beat.log" 2>&1 &
BEAT_PID=$!
success "Celery beat started (PID $BEAT_PID)"

# Save PIDs for the stop script
cat > "$SCRIPT_DIR/.pids" << EOF
BACKEND_PID=$BACKEND_PID
WORKER_PID=$WORKER_PID
BEAT_PID=$BEAT_PID
EOF

# ── 9. Health check ───────────────────────────────────────────────────────────
step "Waiting for backend to be ready"
MAX_WAIT=15
for i in $(seq 1 $MAX_WAIT); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    success "Backend is healthy"
    break
  fi
  if [ "$i" -eq "$MAX_WAIT" ]; then
    warn "Backend did not respond after ${MAX_WAIT}s. Check logs/backend.log"
  fi
  sleep 1
done

# ── Done ─────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}╔══════════════════════════════════════════════╗"
echo -e "║   Bloxp Revived is running!                  ║"
echo -e "╚══════════════════════════════════════════════╝${NC}"
echo -e ""
echo -e "  ${BOLD}App${NC}      → ${BLUE}http://localhost:8000${NC}"
echo -e "  ${BOLD}API docs${NC} → ${BLUE}http://localhost:8000/docs${NC}"
echo -e ""
echo -e "  Logs:"
echo -e "    Backend : tail -f logs/backend.log"
echo -e "    Worker  : tail -f logs/worker.log"
echo -e "    Beat    : tail -f logs/beat.log"
echo -e ""
echo -e "  To stop all services: ${BOLD}./stop.sh${NC}"
echo -e ""
