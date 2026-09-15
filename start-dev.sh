#!/bin/bash
# IPL Fantasy — dev loop.
# Ports: 8014 (api) + 3014 (web). NEVER 8000/3000 — those belong to the NBA app.
# Usage: ./start-dev.sh [--install] [--check]
set -e
cd "$(dirname "$0")"

DO_INSTALL=false
for arg in "$@"; do case $arg in --install) DO_INSTALL=true;; esac; done

if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || true; echo "created .env from .env.example"; fi

if [ "$DO_INSTALL" = true ]; then
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  (cd web && npm install --no-audit --no-fund)
fi

echo "▶ api  http://127.0.0.1:8014  (docs: /api/docs)"
if [ -d .venv ]; then PY=.venv/bin/python; else PY=python3; fi
$PY -m uvicorn api.index:app --port 8014 --host 127.0.0.1 &
API_PID=$!

sleep 3
if ! kill -0 $API_PID 2>/dev/null; then echo "api failed to start"; exit 1; fi

echo "▶ web  http://127.0.0.1:3014"
(cd web && npm run dev &)
WEB_PID=$!

trap "kill $API_PID $WEB_PID 2>/dev/null; exit 0" SIGINT SIGTERM
echo "running — Ctrl+C to stop (api=$API_PID web=$WEB_PID)"
wait
