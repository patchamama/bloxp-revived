@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: deploy.bat -- Bloxp Revived local production deploy (Windows)
::
:: Builds the React frontend, copies dist into the backend, sets up a Python
:: virtual environment, installs all dependencies, and starts FastAPI + Celery.
::
:: Usage:
::   deploy.bat              full deploy
::   deploy.bat --no-build   skip frontend build (reuse existing dist\)
::   deploy.bat --no-venv    skip venv creation (already exists)
::
:: Requirements:
::   - Node.js >= 18  https://nodejs.org
::   - Python >= 3.11 https://python.org
::   - Redis via one of:
::       Memurai (recommended)  https://www.memurai.com
::       WSL2 + Ubuntu          wsl sudo apt install redis-server
::       Docker Desktop         https://www.docker.com/products/docker-desktop
:: =============================================================================

title Bloxp Revived Deploy

:: ── Flags ─────────────────────────────────────────────────────────────────────
set BUILD_FRONTEND=true
set SETUP_VENV=true

for %%A in (%*) do (
  if "%%A"=="--no-build" set BUILD_FRONTEND=false
  if "%%A"=="--no-venv"  set SETUP_VENV=false
  if "%%A"=="--help"     goto :show_help
  if "%%A"=="-h"         goto :show_help
)
goto :start

:show_help
echo deploy.bat -- Bloxp Revived local deploy for Windows
echo.
echo Usage: deploy.bat [--no-build] [--no-venv]
echo   --no-build   Skip frontend build (reuse existing dist\)
echo   --no-venv    Skip venv creation (already exists)
exit /b 0

:start

:: ── Paths ─────────────────────────────────────────────────────────────────────
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set FRONTEND_DIR=%SCRIPT_DIR%\frontend
set BACKEND_DIR=%SCRIPT_DIR%\backend
set STATIC_DIR=%BACKEND_DIR%\static
set VENV_DIR=%BACKEND_DIR%\.venv
set GENERATED_DIR=%SCRIPT_DIR%\generated
set LOG_DIR=%SCRIPT_DIR%\logs

echo.
echo ╔══════════════════════════════════════╗
echo ║   Bloxp Revived -- Local Deploy      ║
echo ╚══════════════════════════════════════╝
echo.

:: ── 1. Prerequisites ──────────────────────────────────────────────────────────
echo [STEP] Checking prerequisites...

where node   >nul 2>&1 || (echo [ERROR] Node.js not found. Install from https://nodejs.org & exit /b 1)
where npm    >nul 2>&1 || (echo [ERROR] npm not found. Reinstall Node.js from https://nodejs.org & exit /b 1)
where python >nul 2>&1 || (echo [ERROR] Python not found. Install from https://python.org & exit /b 1)

for /f "tokens=*" %%v in ('node -v 2^>^&1') do set NODE_VER=%%v
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [INFO]  Node.js !NODE_VER! ^| Python !PY_VER!

:: ── 2. Redis ──────────────────────────────────────────────────────────────────
echo [STEP] Checking Redis...
set REDIS_OK=false

:: Try native redis-cli (Memurai or Windows Redis port already running)
redis-cli ping >nul 2>&1 && set REDIS_OK=true

:: Try to start Memurai service if installed but not running
if "!REDIS_OK!"=="false" (
  sc query memurai >nul 2>&1 && (
    echo [INFO]  Starting Memurai service...
    net start memurai >nul 2>&1
    timeout /t 2 /nobreak >nul
    redis-cli ping >nul 2>&1 && set REDIS_OK=true
  )
)

:: Try WSL -- Redis in WSL2 is reachable at localhost:6379
if "!REDIS_OK!"=="false" (
  where wsl >nul 2>&1 && (
    echo [INFO]  Attempting Redis via WSL...
    wsl redis-cli ping >nul 2>&1 && (
      echo [INFO]  Redis already running inside WSL.
      set REDIS_OK=true
    ) || (
      wsl sudo service redis-server start >nul 2>&1
      timeout /t 2 /nobreak >nul
      wsl redis-cli ping >nul 2>&1 && set REDIS_OK=true
    )
  )
)

:: Try Docker Desktop
if "!REDIS_OK!"=="false" (
  where docker >nul 2>&1 && (
    echo [INFO]  Starting Redis via Docker...
    docker start bloxp-redis >nul 2>&1 || docker run -d --name bloxp-redis -p 6379:6379 redis:7-alpine >nul 2>&1
    timeout /t 3 /nobreak >nul
    redis-cli ping >nul 2>&1 && set REDIS_OK=true
  )
)

if "!REDIS_OK!"=="false" (
  echo [ERROR] Redis not reachable. Choose one option:
  echo   1. Memurai ^(easiest^): https://www.memurai.com
  echo   2. WSL2: wsl sudo apt install redis-server ^&^& wsl sudo service redis-server start
  echo   3. Docker Desktop: docker run -d -p 6379:6379 redis:7-alpine
  exit /b 1
)
echo [OK]    Redis is running

:: Calibre check
where ebook-convert >nul 2>&1 && (
  echo [OK]    Calibre found -- Mobi output enabled
) || (
  echo [WARN]  Calibre not found -- Mobi output disabled ^(ePub and PDF still work^)
)

:: ── 3. Build frontend ─────────────────────────────────────────────────────────
if "!BUILD_FRONTEND!"=="true" (
  echo [STEP] Building React frontend...
  cd /d "!FRONTEND_DIR!"
  echo [INFO]  Installing npm dependencies...
  call npm install --silent
  if errorlevel 1 ( echo [ERROR] npm install failed & exit /b 1 )
  echo [INFO]  Running production build...
  call npm run build
  if errorlevel 1 ( echo [ERROR] Frontend build failed & exit /b 1 )
  echo [OK]    Frontend built -^> !FRONTEND_DIR!\dist
) else (
  echo [INFO]  Skipping frontend build ^(--no-build^)
  if not exist "!FRONTEND_DIR!\dist" (
    echo [ERROR] No dist\ folder found. Run without --no-build first.
    exit /b 1
  )
)

:: ── 4. Copy dist → backend\static ─────────────────────────────────────────────
echo [STEP] Copying frontend dist to backend\static...
if exist "!STATIC_DIR!" rmdir /s /q "!STATIC_DIR!"
xcopy /E /I /Q "!FRONTEND_DIR!\dist" "!STATIC_DIR!" >nul
if errorlevel 1 ( echo [ERROR] xcopy failed & exit /b 1 )
echo [OK]    Copied to !STATIC_DIR!

:: ── 5. Python virtual environment ─────────────────────────────────────────────
if "!SETUP_VENV!"=="true" (
  echo [STEP] Setting up Python virtual environment...
  cd /d "!BACKEND_DIR!"
  if exist "!VENV_DIR!" (
    echo [INFO]  Virtual environment exists, updating...
  ) else (
    echo [INFO]  Creating virtual environment at !VENV_DIR!...
    python -m venv "!VENV_DIR!"
    if errorlevel 1 ( echo [ERROR] python -m venv failed & exit /b 1 )
  )
  echo [INFO]  Installing Python dependencies...
  call "!VENV_DIR!\Scripts\pip.exe" install --upgrade pip --quiet
  call "!VENV_DIR!\Scripts\pip.exe" install -r requirements.txt --quiet
  if errorlevel 1 ( echo [ERROR] pip install failed & exit /b 1 )
  echo [OK]    Python dependencies installed
) else (
  echo [INFO]  Skipping venv setup ^(--no-venv^)
  if not exist "!VENV_DIR!" (
    echo [ERROR] No .venv found. Run without --no-venv first.
    exit /b 1
  )
)

:: ── 6. Runtime directories ────────────────────────────────────────────────────
echo [STEP] Creating runtime directories...
if not exist "!GENERATED_DIR!" mkdir "!GENERATED_DIR!"
if not exist "!LOG_DIR!"       mkdir "!LOG_DIR!"
echo [OK]    Directories ready: generated\ logs\

:: ── 7. Write .env if missing ──────────────────────────────────────────────────
set ENV_FILE=!BACKEND_DIR!\.env
if not exist "!ENV_FILE!" (
  echo [STEP] Creating default .env...
  (
    echo REDIS_URL=redis://localhost:6379/0
    echo GENERATED_DIR=../generated
    echo SMTP_HOST=
    echo SMTP_PORT=587
    echo SMTP_USER=
    echo SMTP_PASS=
  ) > "!ENV_FILE!"
  echo [OK]    Created !ENV_FILE! -- edit it to configure SMTP
) else (
  echo [INFO]  .env already exists, skipping
)

:: ── 8. Kill previous processes ────────────────────────────────────────────────
echo [STEP] Stopping any previous Bloxp processes...
taskkill /F /FI "WINDOWTITLE eq bloxp-backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq bloxp-worker"  >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq bloxp-beat"    >nul 2>&1
echo [OK]    Previous processes cleared

:: ── 9. Start services ─────────────────────────────────────────────────────────
echo [STEP] Starting Bloxp services...
cd /d "!BACKEND_DIR!"

:: FastAPI (uvicorn: 1 worker only on Windows -- no fork() support)
start "bloxp-backend" /MIN cmd /c ^"^"!VENV_DIR!\Scripts\uvicorn.exe^" main:app --host 0.0.0.0 --port 8000 --workers 1 >> "!LOG_DIR!\backend.log" 2>&1^"
echo [OK]    Backend starting ^(PID unknown^) -^> http://localhost:8000

:: Celery worker (-P solo: Windows has no fork, use solo or gevent pool)
start "bloxp-worker" /MIN cmd /c ^"^"!VENV_DIR!\Scripts\celery.exe^" -A tasks.celery_app worker --loglevel=info -P solo >> "!LOG_DIR!\worker.log" 2>&1^"
echo [OK]    Celery worker starting

:: Celery beat
start "bloxp-beat" /MIN cmd /c ^"^"!VENV_DIR!\Scripts\celery.exe^" -A tasks.celery_app beat --loglevel=info >> "!LOG_DIR!\beat.log" 2>&1^"
echo [OK]    Celery beat starting

:: ── 10. Health check ──────────────────────────────────────────────────────────
echo [STEP] Waiting for backend to be ready...
set /a WAIT=0
set /a MAX_WAIT=15

:health_loop
timeout /t 1 /nobreak >nul
curl -sf http://localhost:8000/api/health >nul 2>&1 && goto :healthy
set /a WAIT+=1
if !WAIT! LSS !MAX_WAIT! goto :health_loop
echo [WARN]  Backend did not respond after %MAX_WAIT%s. Check logs\backend.log
goto :done

:healthy
echo [OK]    Backend is healthy

:done
echo.
echo ╔══════════════════════════════════════════════╗
echo ║   Bloxp Revived is running!                  ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   App      -^> http://localhost:8000
echo   API docs -^> http://localhost:8000/docs
echo.
echo   Logs:
echo     Backend : type logs\backend.log
echo     Worker  : type logs\worker.log
echo     Beat    : type logs\beat.log
echo.
echo   To stop: close the bloxp-backend / bloxp-worker / bloxp-beat windows,
echo            or run taskkill /F /FI "WINDOWTITLE eq bloxp-*"
echo.

endlocal
