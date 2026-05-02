@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "LOG_DIR=%SCRIPT_DIR%logs"
set "PIDS_FILE=%SCRIPT_DIR%.pids"
set "PORT=8001"

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [ERROR] Missing virtualenv at "%VENV_DIR%"
  echo Run deploy.bat first.
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
  taskkill /PID %%p /F >nul 2>&1
)

for /f "tokens=2" %%p in ('tasklist /v ^| findstr /i "celery.exe"') do (
  taskkill /PID %%p /F >nul 2>&1
)

pushd "%BACKEND_DIR%"

start "bloxp-backend" /B "%VENV_DIR%\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port %PORT% > "%LOG_DIR%\backend.log" 2>&1
start "bloxp-worker" /B "%VENV_DIR%\Scripts\python.exe" -m celery -A tasks.celery_app:celery_app worker --loglevel=info --concurrency=2 > "%LOG_DIR%\worker.log" 2>&1
start "bloxp-beat" /B "%VENV_DIR%\Scripts\python.exe" -m celery -A tasks.celery_app beat --loglevel=info > "%LOG_DIR%\beat.log" 2>&1

popd

echo [OK] Backend starting on http://localhost:%PORT%
echo [OK] Logs in "%LOG_DIR%"
echo [INFO] Use stop.bat or Task Manager to stop processes.

endlocal
