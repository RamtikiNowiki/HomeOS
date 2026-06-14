#!/usr/bin/env bash
# Bootstrap Home OS Hub on Raspberry Pi OS (Lite).
# Run on the Pi from repo root: bash scripts/pi-bootstrap.sh
#
# Installs Docker (if needed), creates .env with secrets, builds and starts the stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Home OS Hub — Pi bootstrap"
echo "    $(uname -m) @ $(hostname -I | awk '{print $1}')"
echo ""

# ── Docker ───────────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "${USER}" || true
  echo "    Docker installed. If 'docker' fails below, run: newgrp docker"
else
  echo "==> Docker already installed"
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin missing. Re-run get.docker.com or install docker-compose-plugin."
  exit 1
fi

# Use sudo if user not in docker group yet
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
  echo "==> Using sudo for docker (log out/in later to skip sudo)"
fi

# ── .env ─────────────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example (random secrets)..."
  cp .env.example .env
  SECRET_KEY=$(openssl rand -hex 32)
  POSTGRES_PASSWORD=$(openssl rand -hex 16)
  # Default login passcodes — change in .env or here before first run
  SEED_USER1_PASSWORD="${SEED_USER1_PASSWORD:-changeme-ram}"
  SEED_USER2_PASSWORD="${SEED_USER2_PASSWORD:-changeme-aylin}"

  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env
  sed -i "s|^SEED_USER1_PASSWORD=.*|SEED_USER1_PASSWORD=${SEED_USER1_PASSWORD}|" .env
  sed -i "s|^SEED_USER2_PASSWORD=.*|SEED_USER2_PASSWORD=${SEED_USER2_PASSWORD}|" .env
  sed -i "s|^SEED_DEMO_DATA=.*|SEED_DEMO_DATA=0|" .env

  echo ""
  echo "    ┌─────────────────────────────────────────────────────────┐"
  echo "    │  SAVE THESE — login passcodes for the web app           │"
  echo "    ├─────────────────────────────────────────────────────────┤"
  echo "    │  Ram:   user ram   password ${SEED_USER1_PASSWORD}"
  echo "    │  Aylin: user aylin password ${SEED_USER2_PASSWORD}"
  echo "    └─────────────────────────────────────────────────────────┘"
  echo "    Edit ~/home-os-hub/.env anytime to change passwords."
  echo ""
else
  echo "==> .env already exists — keeping it"
fi

# ── Build & run ──────────────────────────────────────────────────────────────
echo "==> Building images (first run takes several minutes on Pi)..."
"${DOCKER[@]}" compose build

echo "==> Starting stack (web + postgres + nginx)..."
"${DOCKER[@]}" compose up -d

echo "==> Waiting for health..."
sleep 5
for i in $(seq 1 30); do
  if curl -fsS --max-time 2 http://127.0.0.1/login >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

LAN_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=============================================="
echo "  Home OS Hub is up!"
echo ""
echo "  On this network:  http://${LAN_IP}/"
echo "  Login: ram / aylin (passwords in .env)"
echo ""
echo "  Logs:    docker compose logs -f web"
echo "  Stop:    docker compose down"
echo "  Restart: docker compose up -d"
echo "=============================================="
