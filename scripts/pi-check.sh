#!/usr/bin/env bash
# Readiness check for Raspberry Pi production deploy.
# Run from repo root: bash scripts/pi-check.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
ok()  { echo -e "${GREEN}✓${NC} $*"; }
warn(){ echo -e "${YELLOW}!${NC} $*"; }
fail(){ echo -e "${RED}✗${NC} $*"; exit 1; }

echo "Home OS Hub — Pi readiness check"
echo "================================="
echo "Arch: $(uname -m)"
echo "Repo: $ROOT"
echo ""

[[ -f docker-compose.yml ]] || fail "docker-compose.yml missing — run from repo root"
[[ -f Dockerfile ]] || fail "Dockerfile missing"
[[ -f nginx/nginx.conf ]] || fail "nginx/nginx.conf missing"
[[ -f requirements-lock.txt ]] || fail "requirements-lock.txt missing"
ok "Project files present"

if [[ -f .env ]]; then
  ok ".env exists"
  # shellcheck disable=SC1091
  set -a && source .env && set +a
  [[ -n "${SECRET_KEY:-}" ]] || warn "SECRET_KEY empty in .env"
  [[ -n "${POSTGRES_PASSWORD:-}" ]] || warn "POSTGRES_PASSWORD empty in .env"
  [[ -n "${SEED_USER1_PASSWORD:-}" ]] || warn "SEED_USER1_PASSWORD empty in .env"
  [[ -n "${SEED_USER2_PASSWORD:-}" ]] || warn "SEED_USER2_PASSWORD empty in .env"
else
  warn ".env missing — run: bash scripts/pi-bootstrap.sh"
fi

if command -v docker >/dev/null 2>&1; then
  ok "Docker: $(docker --version)"
  if docker compose version >/dev/null 2>&1; then
    ok "Compose: $(docker compose version)"
  else
    fail "docker compose plugin not found"
  fi
  if docker info >/dev/null 2>&1; then
    ok "Docker daemon reachable (user in docker group or root)"
  else
    warn "Docker installed but daemon not usable — try: sudo usermod -aG docker \$USER && newgrp docker"
  fi
else
  warn "Docker not installed — pi-bootstrap.sh will install it"
fi

if command -v curl >/dev/null 2>&1; then
  LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  if [[ -n "$LAN_IP" ]] && curl -fsS --max-time 2 "http://127.0.0.1/login" >/dev/null 2>&1; then
    ok "App responding on http://127.0.0.1 (via nginx)"
    echo ""
    echo "  Open on phone: http://${LAN_IP}/"
  elif docker compose ps 2>/dev/null | grep -q Up; then
    warn "Containers running but http://127.0.0.1 not ready yet — wait 30s or: docker compose logs -f web"
  else
    warn "Stack not running — start with: docker compose up -d --build"
  fi
else
  warn "curl not installed (optional)"
fi

echo ""
echo "Done."
