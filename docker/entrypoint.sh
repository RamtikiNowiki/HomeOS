#!/bin/sh
# Wait for Postgres, initialize/seed the database, then start the app.
set -e

echo "[entrypoint] waiting for database..."
python - <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
if url.startswith("sqlite"):
    sys.exit(0)

parsed = urlparse(url)
host, port = parsed.hostname or "db", parsed.port or 5432

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[entrypoint] database reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1)

print("[entrypoint] database never became reachable", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] running idempotent seed..."
python seed.py

echo "[entrypoint] starting: $*"
exec "$@"
