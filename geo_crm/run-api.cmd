@echo off
setlocal
REM GEO-CRM : Uvicorn avec PYTHONPATH = racine du dépôt (équivalent de run-api.sh sur Windows).
cd /d "%~dp0.."
set "REPO_ROOT=%cd%"
set "PYTHONPATH=%REPO_ROOT%"
cd /d "%REPO_ROOT%\geo_crm\backend"
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  "%REPO_ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
) else (
  where python >nul 2>&1 && (
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
  ) || (
    echo ERR: Python introuvable. Creez un venv a la racine du depot : python -m venv .venv
    exit /b 1
  )
)
