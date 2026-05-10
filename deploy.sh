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
#   - Python >= 3.10
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

install_help() {
  local what="$1"
  echo -e "${YELLOW}How to install ${what}:${NC}"
  if [ "$OS" = "Linux" ]; then
    case "$what" in
      "Node.js") echo "  Ubuntu: sudo apt-get update && sudo apt-get install -y nodejs npm" ;;
      "Python 3.10+") echo "  Ubuntu: sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip" ;;
      "Redis") echo "  Ubuntu: sudo apt-get update && sudo apt-get install -y redis-server && sudo systemctl start redis-server" ;;
      *) echo "  Ubuntu: use apt-get to install ${what}" ;;
    esac
  elif [ "$OS" = "Darwin" ]; then
    case "$what" in
      "Node.js") echo "  macOS: brew install node" ;;
      "Python 3.10+") echo "  macOS: brew install python" ;;
      "Redis") echo "  macOS: brew install redis && brew services start redis" ;;
      *) echo "  macOS: brew install ${what}" ;;
    esac
  fi
}

set_env_kv() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

prompt_default() {
  local label="$1" default="$2" out
  read -r -p "${label} [${default}]: " out || true
  echo "${out:-$default}"
}

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
  command -v node  >/dev/null 2>&1 || { install_help "Node.js"; error "Node.js not found."; }
  command -v npm   >/dev/null 2>&1 || { install_help "Node.js"; error "npm not found."; }
  command -v python3 >/dev/null 2>&1 || { install_help "Python 3.10+"; error "Python 3 not found."; }
else
  command -v node  >/dev/null 2>&1 || { install_help "Node.js"; error "Node.js not found."; }
  command -v npm   >/dev/null 2>&1 || { install_help "Node.js"; error "npm not found."; }
  command -v python3 >/dev/null 2>&1 || { install_help "Python 3.10+"; error "Python 3 not found."; }
fi

NODE_VER=$(node -v | sed 's/v//')
PY_VER=$(python3 --version | awk '{print $2}')
info "Node.js $NODE_VER | Python $PY_VER"
python3 - <<'PY' || error "Python 3.10+ required."
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY

# ── Check / install / start Redis ─────────────────────────────────────────────
if ! redis-cli ping >/dev/null 2>&1; then
  warn "Redis is not running. Attempting to start..."
  if [ "$OS" = "Linux" ]; then
    if ! command -v redis-server >/dev/null 2>&1; then
      info "Installing Redis via apt..."
      sudo apt-get update -qq \
        && sudo apt-get install -y redis-server >/dev/null 2>&1 \
        || { install_help "Redis"; error "Could not install Redis."; }
    fi
    if command -v systemctl >/dev/null 2>&1; then
      sudo systemctl start redis-server 2>/dev/null \
        || sudo service redis-server start 2>/dev/null \
        || redis-server --daemonize yes 2>/dev/null \
        || { install_help "Redis"; error "Could not start Redis."; }
    else
      sudo service redis-server start 2>/dev/null \
        || redis-server --daemonize yes 2>/dev/null \
        || { install_help "Redis"; error "Could not start Redis."; }
    fi
  elif [ "$OS" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew services start redis >/dev/null 2>&1 \
        || { install_help "Redis"; error "Could not start Redis."; }
    else
      install_help "Redis"
      error "Redis is not running."
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

info "Installing Playwright browser (Chromium)..."
"$VENV_DIR/bin/python" -m playwright install chromium 2>&1 | grep -v "^$" || warn "Playwright browser install failed — Wix browser discovery will be disabled"
if [ "$OS" = "Linux" ]; then
  info "Installing Playwright system dependencies..."
  "$VENV_DIR/bin/playwright" install-deps chromium >/dev/null 2>&1 \
    || warn "Playwright system deps install failed — run: sudo playwright install-deps chromium"
fi
success "Playwright ready"

command -v celery >/dev/null 2>&1 || error "Celery not available in venv after pip install (check backend/requirements.txt)."
python - <<'PY' || error "Redis Python client missing in venv."
import redis
print(redis.__version__)
PY

# ── 5. Create required directories ────────────────────────────────────────────
step "Creating runtime directories"
mkdir -p "$GENERATED_DIR" "$LOG_DIR"
success "Directories ready: generated/ logs/"

# ── 6. Create/update backend .env ─────────────────────────────────────────────
ENV_FILE="$BACKEND_DIR/.env"
step "Configuring backend .env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
  success "Created $ENV_FILE from .env.example"
fi

if [ -t 0 ]; then
  APP_VERSION_DEFAULT="$(grep '^APP_VERSION=' "$ENV_FILE" | cut -d= -f2- || true)"
  MAX_POSTS_LIMIT_DEFAULT="$(grep '^MAX_POSTS_LIMIT=' "$ENV_FILE" | cut -d= -f2- || true)"
  PAGE_CACHE_TTL_DEFAULT="$(grep '^PAGE_CACHE_TTL_SECONDS=' "$ENV_FILE" | cut -d= -f2- || true)"
  PROCESSED_POST_CACHE_TTL_DEFAULT="$(grep '^PROCESSED_POST_CACHE_TTL_SECONDS=' "$ENV_FILE" | cut -d= -f2- || true)"
  JOB_TTL_DEFAULT="$(grep '^JOB_TTL_SECONDS=' "$ENV_FILE" | cut -d= -f2- || true)"
  ADMIN_SECRET_DEFAULT="$(grep '^ADMIN_AUTH_SECRET=' "$ENV_FILE" | cut -d= -f2- || true)"
  ADMIN_TOKEN_TTL_DEFAULT="$(grep '^ADMIN_TOKEN_TTL_SECONDS=' "$ENV_FILE" | cut -d= -f2- || true)"
  MAX_CONCURRENT_JOBS_DEFAULT="$(grep '^MAX_CONCURRENT_JOBS=' "$ENV_FILE" | cut -d= -f2- || true)"
  REDIS_URL_DEFAULT="$(grep '^REDIS_URL=' "$ENV_FILE" | cut -d= -f2- || true)"
  GENERATED_DIR_DEFAULT="$(grep '^GENERATED_DIR=' "$ENV_FILE" | cut -d= -f2- || true)"
  CALIBRE_PATH_DEFAULT="$(grep '^CALIBRE_EBOOK_CONVERT_PATH=' "$ENV_FILE" | cut -d= -f2- || true)"
  SMTP_HOST_DEFAULT="$(grep '^SMTP_HOST=' "$ENV_FILE" | cut -d= -f2- || true)"
  SMTP_PORT_DEFAULT="$(grep '^SMTP_PORT=' "$ENV_FILE" | cut -d= -f2- || true)"
  SMTP_USER_DEFAULT="$(grep '^SMTP_USER=' "$ENV_FILE" | cut -d= -f2- || true)"
  SMTP_PASS_DEFAULT="$(grep '^SMTP_PASS=' "$ENV_FILE" | cut -d= -f2- || true)"
  ADMIN_USERS_DEFAULT="$(grep '^ADMIN_USERS_JSON=' "$ENV_FILE" | cut -d= -f2- || true)"

  APP_VERSION_VAL="$(prompt_default "APP_VERSION" "${APP_VERSION_DEFAULT:-2.1.8}")"
  MAX_POSTS_LIMIT_VAL="$(prompt_default "MAX_POSTS_LIMIT" "${MAX_POSTS_LIMIT_DEFAULT:-9999}")"
  PAGE_CACHE_TTL_VAL="$(prompt_default "PAGE_CACHE_TTL_SECONDS" "${PAGE_CACHE_TTL_DEFAULT:-86400}")"
  PROCESSED_POST_CACHE_TTL_VAL="$(prompt_default "PROCESSED_POST_CACHE_TTL_SECONDS" "${PROCESSED_POST_CACHE_TTL_DEFAULT:-86400}")"
  JOB_TTL_VAL="$(prompt_default "JOB_TTL_SECONDS (ebooks/job persistence)" "${JOB_TTL_DEFAULT:-86400}")"
  ADMIN_SECRET_VAL="$(prompt_default "ADMIN_AUTH_SECRET" "${ADMIN_SECRET_DEFAULT:-change-me-dev-secret}")"
  ADMIN_TOKEN_TTL_VAL="$(prompt_default "ADMIN_TOKEN_TTL_SECONDS" "${ADMIN_TOKEN_TTL_DEFAULT:-28800}")"
  MAX_CONCURRENT_JOBS_VAL="$(prompt_default "MAX_CONCURRENT_JOBS" "${MAX_CONCURRENT_JOBS_DEFAULT:-2}")"
  REDIS_URL_VAL="$(prompt_default "REDIS_URL" "${REDIS_URL_DEFAULT:-redis://localhost:6379/0}")"
  GENERATED_DIR_VAL="$(prompt_default "GENERATED_DIR" "${GENERATED_DIR_DEFAULT:-../generated}")"
  CALIBRE_PATH_VAL="$(prompt_default "CALIBRE_EBOOK_CONVERT_PATH" "${CALIBRE_PATH_DEFAULT:-/opt/calibre/ebook-convert}")"
  SMTP_HOST_VAL="$(prompt_default "SMTP_HOST" "${SMTP_HOST_DEFAULT:-}")"
  SMTP_PORT_VAL="$(prompt_default "SMTP_PORT" "${SMTP_PORT_DEFAULT:-587}")"
  SMTP_USER_VAL="$(prompt_default "SMTP_USER" "${SMTP_USER_DEFAULT:-}")"
  SMTP_PASS_VAL="$(prompt_default "SMTP_PASS" "${SMTP_PASS_DEFAULT:-}")"

  read -r -p "Configure admin users now? [y/N]: " CFG_ADM || true
  if [[ "${CFG_ADM:-N}" =~ ^[Yy]$ ]]; then
    read -r -p "How many admin users? [1]: " NADM || true
    NADM="${NADM:-1}"
    ADMIN_USERS_VAL="$("$VENV_DIR/bin/python" -c "import json, hashlib, secrets, sys
n = int(${NADM})
users = {}
for i in range(n):
    sys.stderr.write(f'Admin username #{i+1}: ')
    sys.stderr.flush()
    u = input().strip()
    sys.stderr.write(f'Password for {u}: ')
    sys.stderr.flush()
    p = input().strip()
    salt = secrets.token_hex(16)
    it = 200000
    h = hashlib.pbkdf2_hmac('sha256', p.encode(), salt.encode(), it).hex()
    users[u] = f'pbkdf2_sha256\${it}\${salt}\${h}'
print(json.dumps(users, ensure_ascii=False))")"
  else
    ADMIN_USERS_VAL="${ADMIN_USERS_DEFAULT:-{\"admin\":\"pbkdf2_sha256\$200000\$2c4c14d9bfd648aa92da45063abe8e7d\$fa642fc7877bbde4fea1fd6b6bf1bce10f954cad1e698f0314181d20d07e913a\"}}"
  fi

  set_env_kv "$ENV_FILE" "APP_VERSION" "$APP_VERSION_VAL"
  set_env_kv "$ENV_FILE" "MAX_POSTS_LIMIT" "$MAX_POSTS_LIMIT_VAL"
  set_env_kv "$ENV_FILE" "PAGE_CACHE_TTL_SECONDS" "$PAGE_CACHE_TTL_VAL"
  set_env_kv "$ENV_FILE" "PROCESSED_POST_CACHE_TTL_SECONDS" "$PROCESSED_POST_CACHE_TTL_VAL"
  set_env_kv "$ENV_FILE" "JOB_TTL_SECONDS" "$JOB_TTL_VAL"
  set_env_kv "$ENV_FILE" "ADMIN_AUTH_SECRET" "$ADMIN_SECRET_VAL"
  set_env_kv "$ENV_FILE" "ADMIN_TOKEN_TTL_SECONDS" "$ADMIN_TOKEN_TTL_VAL"
  set_env_kv "$ENV_FILE" "MAX_CONCURRENT_JOBS" "$MAX_CONCURRENT_JOBS_VAL"
  set_env_kv "$ENV_FILE" "ADMIN_USERS_JSON" "$ADMIN_USERS_VAL"
  set_env_kv "$ENV_FILE" "REDIS_URL" "$REDIS_URL_VAL"
  set_env_kv "$ENV_FILE" "GENERATED_DIR" "$GENERATED_DIR_VAL"
  set_env_kv "$ENV_FILE" "CALIBRE_EBOOK_CONVERT_PATH" "$CALIBRE_PATH_VAL"
  set_env_kv "$ENV_FILE" "SMTP_HOST" "$SMTP_HOST_VAL"
  set_env_kv "$ENV_FILE" "SMTP_PORT" "$SMTP_PORT_VAL"
  set_env_kv "$ENV_FILE" "SMTP_USER" "$SMTP_USER_VAL"
  set_env_kv "$ENV_FILE" "SMTP_PASS" "$SMTP_PASS_VAL"
  rm -f "$ENV_FILE.bak"
  success "Updated $ENV_FILE"
else
  warn "Non-interactive shell: .env not prompted. Existing values preserved."
fi

# Calibre path validation
CALIBRE_PATH_EFFECTIVE="$(grep '^CALIBRE_EBOOK_CONVERT_PATH=' "$ENV_FILE" | cut -d= -f2- || true)"
if [ -n "$CALIBRE_PATH_EFFECTIVE" ] && [ -x "$CALIBRE_PATH_EFFECTIVE" ]; then
  success "Calibre convert binary found at: $CALIBRE_PATH_EFFECTIVE"
elif command -v ebook-convert >/dev/null 2>&1; then
  warn "Configured Calibre path not executable ($CALIBRE_PATH_EFFECTIVE), but ebook-convert exists in PATH."
else
  warn "Calibre convert binary not found at configured path ($CALIBRE_PATH_EFFECTIVE) and not in PATH."
  if [ "$OS" = "Linux" ]; then
    echo "  Ubuntu: install Calibre and set CALIBRE_EBOOK_CONVERT_PATH (e.g. /opt/calibre/ebook-convert)"
  else
    echo "  macOS: brew install --cask calibre, then set CALIBRE_EBOOK_CONVERT_PATH"
  fi
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
echo -e "  To stop all services: ${BOLD}./stop-local.sh${NC}"
echo -e ""
