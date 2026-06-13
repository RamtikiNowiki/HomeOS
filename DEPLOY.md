# Deploying Home OS Hub on Raspberry Pi 400

## Overview

| Environment | Database | How to run |
|-------------|----------|------------|
| **Local dev (Fedora)** | SQLite (`instance/dev.db`) | `python wsgi.py` — no Postgres needed |
| **Production (Pi)** | PostgreSQL 16 in Docker | `docker compose up -d --build` |

SQLite is automatic when `DATABASE_URL` is unset. Docker Compose injects Postgres for the `web` container.

## First-time Pi setup

```bash
git clone <repo> && cd home-os-hub
cp .env.example .env
nano .env   # fill SECRET_KEY, POSTGRES_PASSWORD, user passcodes
docker compose up -d --build
```

Open `http://<pi-ip>/` — nginx proxies to gunicorn on port 8000 inside the stack.

### Required `.env` values

```bash
SECRET_KEY=<long random string>
POSTGRES_PASSWORD=<strong password>
SEED_USER1_PASSWORD=<ram passcode>
SEED_USER2_PASSWORD=<aylin passcode>
SEED_DEMO_DATA=0          # clean start recommended
```

### Optional integrations (add when home)

```bash
# Home Assistant — long-lived token from HA Profile → Security
HOME_ASSISTANT_URL=http://192.168.1.10:8123
HOME_ASSISTANT_TOKEN=eyJ...
HOME_ASSISTANT_LIGHTS=light.living_room,light.bedroom
HOME_ASSISTANT_SENSOR=sensor.living_room_temperature

# Creality K2 Plus — Moonraker on port 7125
CREALITY_K2_HOST=192.168.1.50
CREALITY_K2_PORT=7125
```

Restart after changing env: `docker compose up -d`

## Architecture

```
Phone/Browser → nginx:80 → web:8000 (gunicorn/Flask)
                              ↓
                           db:5432 (PostgreSQL, volume pgdata)
```

The Pi reaches HA and the K2 on your LAN by IP — no special Docker networking required in most home setups.

## Useful commands

```bash
docker compose logs -f web      # app logs
docker compose exec web python seed.py   # re-run idempotent seed/migrations
docker compose ps
docker compose down             # stop (data persists in pgdata volume)
```

## Local dev (unchanged)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional — DATABASE_URL stays empty
python seed.py
python wsgi.py                  # http://localhost:5000
```

## Home Assistant quick start

1. Install HA OS on your spare Pi (or use existing instance).
2. Add devices in HA first (Ecobee, lights, etc.).
3. Create a **Long-Lived Access Token** in your HA profile.
4. Find entity IDs: **Settings → Devices & Services → entity ID** (e.g. `light.kitchen`).
5. Set env vars on the Home OS Pi and restart.

## K2 Plus / Moonraker quick start

The K2 Plus runs **Klipper + Moonraker** (same API as Voron/other Klipper printers).

1. Find printer IP: printer screen → network, or your router's DHCP list.
2. Test from Pi: `curl http://192.168.x.x:7125/printer/info`
3. Set `CREALITY_K2_HOST=192.168.x.x` in `.env`.
4. Home OS panel shows: progress, temps, layer, fan, pause/resume/cancel.

You can still use **Fluidd/Creality Print** for bed mesh, file uploads, and macros — this hub is for dashboard-at-a-glance control.

## PWA — Install on phone (standalone, no browser bar)

The app is a Progressive Web App. Requirements for **Install app** (not just a bookmark):

| Context | Works? |
|---------|--------|
| `http://127.0.0.1:5000` on your PC (dev) | Yes — test install in Chrome |
| `http://192.168.x.x` from phone | No — HTTP LAN is not a secure context |
| `https://…` via Tailscale Serve (prod) | Yes — use this on phones |

### Dev: test install on your computer

```bash
python wsgi.py
# Open http://127.0.0.1:5000 in Chrome
# DevTools → Application → Manifest (check for errors)
# Address bar → Install app / ⊕
```

Regenerate PNG icons after changing branding:

```bash
pip install Pillow
python scripts/generate_pwa_icons.py
```

### Prod: HTTPS via Tailscale Serve (recommended for phones)

On the Pi 400 (after `tailscale up`):

```bash
# One-time: expose port 80 on your tailnet with HTTPS
sudo tailscale serve --bg http://127.0.0.1:80
# Or if nginx is only inside Docker on host port 80, same command.

# Check status
tailscale serve status
```

Then on your phone (Tailscale connected):

1. Open **`https://<pi-machine-name>.<tailnet>.ts.net`**
2. Chrome → **Install app** (Android) or Safari → **Add to Home Screen** (iPhone)
3. Launch from the **HomeOS** icon — no address bar (`display: standalone`)

Invite Aylin to your tailnet so her iPhone can reach the same HTTPS URL.

### PWA files (reference)

| Path | Purpose |
|------|---------|
| `/manifest.webmanifest` | App name, icons, `standalone` display |
| `/sw.js` | Service worker (site-wide scope) |
| `/static/icons/icon-192.png` | Chrome install icon |
| `/static/icons/icon-512.png` | Splash / install icon |

## HTTPS (optional later)

Put nginx behind Cloudflare tunnel, or add a TLS cert volume and listen 443. Set `COOKIE_SECURE=1` when serving over HTTPS.
