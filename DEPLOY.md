# Deploying Home OS Hub on Raspberry Pi 400

## Should you run production on the Pi?

**Yes** — for a two-user homelab, Docker Compose + Postgres + nginx is the intended production setup. Data survives reboots; HA and printer integrate via `.env` without rebuilding images.

Skip production on the Pi only if you are still actively developing on the device itself — use SQLite on a laptop and deploy when stable.

## Quick start (Pi OS Lite — first time)

SSH into the Pi, then:

```bash
cd ~/HomeOS          # or wherever you cloned
git pull
bash scripts/pi-bootstrap.sh
```

That script will:

1. Install Docker (if missing)
2. Create `.env` with random `SECRET_KEY` / DB password (and default login passcodes)
3. `docker compose up -d --build`
4. Print `http://<pi-lan-ip>/`

Check status anytime:

```bash
bash scripts/pi-check.sh
docker compose ps
docker compose logs -f web
```

**Phones on home Wi‑Fi:** open `http://<pi-lan-ip>/` — same network, no Tailscale required at home.

### Custom login passwords before bootstrap

```bash
export SEED_USER1_PASSWORD='your-pass'
export SEED_USER2_PASSWORD='your-pass'
bash scripts/pi-bootstrap.sh
```

Or edit `.env` after bootstrap (passwords are set at seed time on first boot).

### Manual setup

```bash
cp .env.example .env
nano .env    # SECRET_KEY, POSTGRES_PASSWORD, SEED_*_PASSWORD — all required
docker compose up -d --build
```

## Overview

| Environment | Database | How to run |
|-------------|----------|------------|
| **Local dev** | SQLite (`instance/dev.db`) | `python wsgi.py` — no Postgres needed |
| **Production (Pi)** | PostgreSQL 16 in Docker | `docker compose up -d --build` |

SQLite is automatic when `DATABASE_URL` is unset. Docker Compose injects Postgres for the `web` container.

## First-time Pi setup

```bash
git clone https://github.com/RamtikiNowiki/HomeOS.git && cd HomeOS
cp .env.example .env
nano .env   # fill SECRET_KEY, POSTGRES_PASSWORD, user passcodes
docker compose up -d --build
```

Open `http://<pi-lan-ip>/` — nginx proxies to gunicorn on port 8000 inside the stack.

### Required `.env` values

```bash
SECRET_KEY=<long random string>
POSTGRES_PASSWORD=<strong password>
SEED_USER1_PASSWORD=<passcode>
SEED_USER2_PASSWORD=<passcode>
SEED_DEMO_DATA=0          # clean start recommended
```

### Optional integrations

```bash
# Home Assistant — long-lived token from HA Profile → Security
HOME_ASSISTANT_URL=http://homeassistant:8123    # Docker internal, or http://<pi-lan-ip>:8123
HOME_ASSISTANT_TOKEN=<your-token>
HOME_ASSISTANT_LIGHTS=light.living_room,light.bedroom
HOME_ASSISTANT_SENSOR=sensor.living_room_temperature

# Creality K2 Plus — Moonraker on port 7125
CREALITY_K2_HOST=<printer-lan-ip>
CREALITY_K2_PORT=7125
```

Restart after changing env: `docker compose up -d`

## Architecture

```
Phone/Browser → nginx:80 → web:8000 (gunicorn/Flask)
                              ↓
                           db:5432 (PostgreSQL, volume pgdata)
```

The Pi reaches HA and the K2 on your LAN by IP — bridge networking is sufficient in most home setups.

## Useful commands

```bash
docker compose logs -f web
docker compose exec web python seed.py   # idempotent seed/migrations
docker compose ps
docker compose down                    # stop (data persists in pgdata volume)
```

## Home Assistant (optional container on same Pi)

```bash
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d
```

See [INTEGRATIONS.md](INTEGRATIONS.md) for wiring and token setup.

## K2 Plus / Moonraker

1. Find printer IP: printer screen → network, or router DHCP list.
2. Test from Pi: `curl http://<printer-ip>:7125/printer/info`
3. Set `CREALITY_K2_HOST=<printer-ip>` in `.env`.
4. Home OS panel: progress, temps, preheat, history, pause/resume/cancel.

Use **Fluidd** for bed mesh, file uploads, and macros — this hub is dashboard-at-a-glance control.

## PWA — Install on phone

| Context | Works? |
|---------|--------|
| `http://127.0.0.1:5000` (dev) | Yes — Chrome install |
| `http://192.168.x.x` from phone | No — not a secure context |
| `https://…` via Tailscale Serve | Yes — use for phones |

### Prod: HTTPS via Tailscale Serve

On the Pi (after `tailscale up`):

```bash
sudo tailscale serve --bg http://127.0.0.1:80
tailscale serve status
```

On your phone (Tailscale connected):

1. Open `https://<machine-name>.<tailnet>.ts.net`
2. Chrome → **Install app** / Safari → **Add to Home Screen**
3. Set `COOKIE_SECURE=1` in `.env` and `docker compose up -d`

Invite other household users to your tailnet for the same HTTPS URL.

## HTTPS alternatives

Cloudflare tunnel, or nginx TLS on port 443. Set `COOKIE_SECURE=1` when serving over HTTPS.
