#!/bin/sh
set -eu

TARGET="${TUNNEL_TARGET:-http://agente-voz:8767}"
OUT="/tunnel/public_https_url"

mkdir -p /tunnel

cloudflared tunnel --no-autoupdate --url "$TARGET" 2>&1 | while IFS= read -r line; do
  printf '%s\n' "$line"
  case "$line" in
    *trycloudflare.com*)
      url=$(printf '%s' "$line" | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -n 1 || true)
      if [ -n "$url" ]; then
        printf '%s' "$url" > "$OUT"
      fi
      ;;
  esac
done
