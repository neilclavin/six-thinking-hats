#!/bin/bash
# Six Thinking Hats — one-click launcher for macOS.
# Double-click this file in Finder. First run sets everything up; later runs are instant.

cd "$(dirname "$0")" || exit 1

# 1. Find Python 3.
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo
  echo "  Python 3 isn't installed."
  echo "  Install it from https://www.python.org/downloads/ (or run: xcode-select --install),"
  echo "  then double-click this file again."
  echo
  read -r -p "  Press Return to close." _
  exit 1
fi

# 2. Create the isolated environment + install dependencies on first run.
if [ ! -d ".venv" ]; then
  echo "  First-time setup — installing (this takes a minute)…"
  "$PY" -m venv .venv || { echo "  Could not create environment."; read -r _; exit 1; }
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt || { echo "  Install failed."; read -r _; exit 1; }
fi

# 3. Launch. app.py opens your browser automatically.
echo "  Starting Six Thinking Hats…"
exec ./.venv/bin/python app.py
