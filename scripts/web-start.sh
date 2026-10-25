#!/usr/bin/env bash
# Startet die Web-Oberfläche im Hintergrund, falls sie noch nicht läuft.
# Wird in Codespaces automatisch beim Verbinden ausgeführt.
#   Log:      /tmp/buergerai-web.log
#   Beenden:  pkill -f "buergerai web"
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PORT="${BUERGERAI_PORT:-8000}"
if curl -fsS "http://127.0.0.1:${PORT}/api/gesund" >/dev/null 2>&1; then
  echo "BürgerAI Web läuft bereits auf Port ${PORT}."
  exit 0
fi
setsid nohup ./bai web --port "${PORT}" >/tmp/buergerai-web.log 2>&1 < /dev/null &
for _ in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/gesund" >/dev/null 2>&1; then
    echo "BürgerAI Web gestartet: Port ${PORT} (Reiter 'Ports' → Weltkugel-Symbol)."
    exit 0
  fi
  sleep 0.5
done
echo "Web-Oberfläche ist nicht gestartet. Details: /tmp/buergerai-web.log – manuell starten mit: ./bai web" >&2
exit 1
