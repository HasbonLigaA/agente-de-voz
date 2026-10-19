#!/bin/sh
set -eu

PORT="${PORT:-8767}"
TLS_PORT="${TLS_PORT:-8768}"
CERT="${TLS_CERT_PATH:-/certs/fullchain.pem}"
KEY="${TLS_KEY_PATH:-/certs/key.pem}"

if [ -f "$CERT" ] && [ -f "$KEY" ]; then
  uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" &
  exec uvicorn backend.main:app --host 0.0.0.0 --port "$TLS_PORT" \
    --ssl-certfile "$CERT" --ssl-keyfile "$KEY"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
