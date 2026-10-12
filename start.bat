@echo off
setlocal enableextensions
title eBook Studio AI - launcher

rem ===========================================================================
rem  eBook Studio AI - one-click local launcher (Windows)
rem
rem  Starts the FastAPI backend and the Next.js web app in their own windows,
rem  waits until both respond, then opens the app in your default browser.
rem
rem  Runs fully offline with SQLite + the mock LLM (no Docker, no API keys).
rem  Environment variables set below override anything in a .env file.
rem ===========================================================================

rem Always operate from the repository root (this file's folder).
cd /d "%~dp0"
set "ROOT=%~dp0"
set "API_DIR=%ROOT%apps\api"
set "WEB_DIR=%ROOT%apps\web"

echo ============================================================
echo   eBook Studio AI - starting local development stack
echo ============================================================
echo.

rem --- Prerequisites -------------------------------------------------------
where uv >nul 2>&1
if errorlevel 1 (
  echo [ERROR] "uv" was not found on PATH.
  echo         Install it from https://docs.astral.sh/uv/
  goto :fail
)
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] "node" was not found on PATH. Install Node.js 22+.
  goto :fail
)
where pnpm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] "pnpm" was not found on PATH. Enable it with: corepack enable
  goto :fail
)

rem ---------------------------------------------------------------------------
rem  Local dev settings: SQLite database, mock LLM, inline job execution.
rem ---------------------------------------------------------------------------
set "APP_ENV=development"
set "DATABASE_URL=sqlite+aiosqlite:///./ebook_studio.db"
set "LLM_PROVIDER=mock"
set "JOB_EXECUTION_MODE=inline"
set "STORAGE_BACKEND=local"

rem --- Backend --------------------------------------------------------------
echo [1/3] Syncing the API environment (uv)...
pushd "%API_DIR%"
uv sync --group dev || (popd & goto :fail)

echo [2/3] Preparing the database and demo data...
uv run python -m app.scripts.seed || (popd & goto :fail)
popd

rem --- Frontend -------------------------------------------------------------
if not exist "%WEB_DIR%\.env.local" (
  echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000>"%WEB_DIR%\.env.local"
)
if not exist "%WEB_DIR%\node_modules" (
  echo [3/3] Installing web dependencies with pnpm...
  pushd "%WEB_DIR%"
  call pnpm install || (popd & goto :fail)
  popd
) else (
  echo [3/3] Web dependencies already installed.
)

rem --- Launch both servers in their own windows -----------------------------
echo.
echo Starting the API and web servers in separate windows...
start "eBook Studio API" /D "%API_DIR%" cmd /k "uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "eBook Studio Web" /D "%WEB_DIR%" cmd /k "pnpm dev"

echo Waiting for the servers to be ready (this can take a moment)...
call :waiturl "http://localhost:8000/api/v1/health"
call :waiturl "http://localhost:3000"

echo Opening the app in your browser...
start "" "http://localhost:3000"

echo.
echo ============================================================
echo   eBook Studio AI is running
echo.
echo     Web app  : http://localhost:3000
echo     API docs : http://localhost:8000/docs
echo.
echo   Demo login : demo@ebookstudio.local / demo-pass-123
echo   Admin login: admin@ebookstudio.local / admin-pass-123
echo.
echo   To stop the app, close the "eBook Studio API" and
echo   "eBook Studio Web" windows (or just this whole session).
echo ============================================================
echo.
pause
goto :eof

rem --- Helper: block until a URL answers with HTTP 200 ----------------------
:waiturl
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='%~1'; for($i=0;$i -lt 240;$i++){ try{ if((Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2).StatusCode -eq 200){ exit 0 } }catch{}; Start-Sleep -Milliseconds 500 }; exit 1"
exit /b %errorlevel%

:fail
echo.
echo Startup aborted. Fix the problem above and try again.
pause
exit /b 1
