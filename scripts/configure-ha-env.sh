#!/usr/bin/env bash
# Wire Home Assistant into Home OS .env (run on the Pi in ~/HomeOS).
#
# Usage:
#   ./scripts/configure-ha-env.sh \
#     http://192.168.1.55:8123 \
#     eyJhbGci...long-lived-token... \
#     light.living_room,light.bedroom \
#     sensor.living_room_temperature
#
# Then: docker compose up -d

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

URL="${1:-}"
TOKEN="${2:-}"
LIGHTS="${3:-}"
SENSOR="${4:-}"

if [[ -z "$URL" || -z "$TOKEN" ]]; then
  echo "Usage: $0 <HA_URL> <HA_TOKEN> [LIGHTS_CSV] [SENSOR_ENTITY]" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy .env.example first." >&2
  exit 1
fi

set_var() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_var HOME_ASSISTANT_URL "$URL"
set_var HOME_ASSISTANT_TOKEN "$TOKEN"
[[ -n "$LIGHTS" ]] && set_var HOME_ASSISTANT_LIGHTS "$LIGHTS"
[[ -n "$SENSOR" ]] && set_var HOME_ASSISTANT_SENSOR "$SENSOR"

echo "Updated Home Assistant vars in $ENV_FILE"
echo "Restarting web container..."
cd "$ROOT"
docker compose up -d web

echo "Testing HA from web container..."
docker compose exec -T web python - <<'PY'
import os, urllib.request, json, sys
url = os.environ.get("HOME_ASSISTANT_URL", "").rstrip("/")
token = os.environ.get("HOME_ASSISTANT_TOKEN", "")
req = urllib.request.Request(f"{url}/api/", headers={"Authorization": f"Bearer {token}"})
try:
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode())
    print("HA API OK:", data.get("message", data))
except Exception as e:
    print("HA API FAILED:", e, file=sys.stderr)
    sys.exit(1)
PY

echo "Done. Open Home OS → Home panel to verify lights/sensor."
