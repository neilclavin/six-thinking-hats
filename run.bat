@echo off
REM Six Thinking Hats - one-click launcher for Windows.
REM Double-click this file. First run sets everything up; later runs are instant.

cd /d "%~dp0"

REM 1. Find Python.
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python isn't installed.
  echo   Install it from https://www.python.org/downloads/
  echo   IMPORTANT: tick "Add Python to PATH" in the installer, then run this file again.
  echo.
  pause
  exit /b 1
)

REM 2. Create the isolated environment + install dependencies on first run.
if not exist ".venv" (
  echo   First-time setup - installing ^(this takes a minute^)...
  python -m venv .venv || (echo   Could not create environment. & pause & exit /b 1)
  ".venv\Scripts\python" -m pip install --quiet --upgrade pip
  ".venv\Scripts\pip" install --quiet -r requirements.txt || (echo   Install failed. & pause & exit /b 1)
)

REM 3. Launch. app.py opens your browser automatically.
echo   Starting Six Thinking Hats...
".venv\Scripts\python" app.py
pause
