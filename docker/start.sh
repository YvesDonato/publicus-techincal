#!/bin/sh
set -eu

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-3000}"
BACKEND_HOST="${BACKEND_HOST:-$HOST}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
INTERNAL_BACKEND_API_URL="${INTERNAL_BACKEND_API_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"

export HOST
export PORT
export BACKEND_HOST
export BACKEND_PORT
export INTERNAL_BACKEND_API_URL

if [ -z "${BACKEND_API_URL+x}" ]; then
  export BACKEND_API_URL=""
fi

uvicorn publicus_backend.app:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
backend_pid="$!"

node /app/frontend/build/index.js &
frontend_pid="$!"

shutdown() {
  kill -TERM "$frontend_pid" "$backend_pid" 2>/dev/null || true
  wait "$frontend_pid" 2>/dev/null || true
  wait "$backend_pid" 2>/dev/null || true
}

trap 'shutdown; exit 143' INT TERM

while true; do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    set +e
    wait "$backend_pid"
    status="$?"
    set -e
    shutdown
    exit "$status"
  fi

  if ! kill -0 "$frontend_pid" 2>/dev/null; then
    set +e
    wait "$frontend_pid"
    status="$?"
    set -e
    shutdown
    exit "$status"
  fi

  sleep 2
done
