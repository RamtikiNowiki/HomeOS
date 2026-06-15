# Integrations — K2, Home Assistant, architecture

Recommended order and where each component runs.

## Architecture

```
Phones ──Tailscale HTTPS──► Home OS Pi (<pi-lan-ip>)
                              │ Flask + Postgres + nginx
                              │
              LAN REST API    │    LAN Moonraker :7125
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Home Assistant          K2 Plus
         (Docker on Pi or            (Helper Script
          separate device)            on printer)
```

Home OS talks to HA and the printer over HTTP on your LAN — not inside the Flask container.

| Component | Where it runs | Why |
|-----------|---------------|-----|
| Home OS Hub | Pi 400 | Fitness + dashboard + API glue |
| Home Assistant | Same Pi (Docker) or separate device | Device hub |
| K2 Moonraker | On the printer | Already there |
| K2 Helper Script | On the printer | Camera bridge for Fluidd / Home OS |

---

## 1. K2 camera — Helper Script (on the printer)

Community installer for Creality K2 — you do not write custom scripts.

- [K2 Plus Helper Script wiki](https://github.com/sw3defy/Creality-Helper-Script-Wiki-K2-Plus)
- [Guilouz Creality Helper Script](https://github.com/Guilouz/Creality-Helper-Script)

### Install camera support (option 11)

1. Open **Fluidd**: `http://<printer-ip>:4408`
2. Open **Terminal** (or SSH to the printer).
3. Run: `sh /mnt/UDISK/helper-script/helper.sh` (install helper first if missing — see wiki).
4. Choose **11) Camera Support for Fluidd and Mainsail**.
5. Reboot printer; wait ~60–90 seconds.
6. Verify: `curl http://<printer-ip>:7125/server/webcams/list` — should not be empty `[]`.
7. Refresh **Home OS → Printer** — camera embeds automatically.

Until then, use **Fluidd ↗** on the printer panel.

---

## 2. K2 features in Home OS

| Feature | Status |
|---------|--------|
| Live status, pause/resume/cancel | ✅ |
| Preheat presets (PLA/PETG/ABS/cool down) | ✅ |
| Recent print history | ✅ |
| Embedded camera | After Helper Script #11 |
| Print-complete notification | Later (HA automation) |

---

## 3. Home Assistant

### Option A — Separate Pi (ideal for heavy setups)

1. Flash [Home Assistant OS](https://www.home-assistant.io/installation/raspberrypi).
2. Onboard at `http://<ha-ip>:8123`.
3. Add integrations (Govee, Ecobee, etc.).
4. Create long-lived token: **Profile → Security**.
5. On Home OS Pi:

```bash
cd ~/HomeOS
./scripts/configure-ha-env.sh \
  http://<ha-ip>:8123 \
  '<your-token>' \
  'light.living_room,light.bedroom' \
  'sensor.living_room_temperature'
```

### Option B — HA container on same Pi 400

```bash
cd ~/HomeOS
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d
```

Onboard at `http://<pi-lan-ip>:8123`, create token, then:

```bash
./scripts/configure-ha-env.sh http://homeassistant:8123 '<your-token>'
```

Using `http://homeassistant:8123` keeps traffic on the Docker network (recommended for the web container).

### Wiring summary

```bash
HOME_ASSISTANT_URL=http://homeassistant:8123
HOME_ASSISTANT_TOKEN=<token>
HOME_ASSISTANT_LIGHTS=light.living_room,light.desk
HOME_ASSISTANT_SENSOR=sensor.living_room_temperature
```

Restart: `docker compose up -d`

---

## 4. Suggested order

1. Home OS on Pi + Tailscale HTTPS
2. K2 Moonraker in `.env`
3. Helper Script camera on printer
4. Home Assistant (container or separate Pi)
5. Add Govee / Ecobee in HA
6. Run `configure-ha-env.sh`
7. **Pi 5 node:** Ollama + Hermes Agent → HA over LAN → future “Ask Home” in Flask

### Future: Hermes + Ollama (Pi 5)

| Piece | Role |
|-------|------|
| **Pi 400** | Home OS + Home Assistant (unchanged) |
| **Pi 5 8GB** | Ollama (local LLM) + Hermes Agent |
| **Hermes → HA** | REST/WebSocket — control lights, climate, automations |
| **Home OS → Hermes** | Planned “Ask Home” chat panel in Flask |
| **Telegram** | Optional Hermes channel for away-from-home commands |

Example future flow: user types *“turn off all lights”* in Home OS → Flask calls Hermes API on Pi 5 → Hermes calls HA services → lights off.

---

## 5. Home OS vs Home Assistant

| Task | Use |
|------|-----|
| Gym logging, charts, PWA | Home OS |
| Quick light toggles | Home OS (via HA API) |
| Device pairing, automations, scenes | Home Assistant |
| Printer at-a-glance | Home OS |
| Bed mesh, uploads, macros | Fluidd |
