# Integrations roadmap — K2, Home Assistant, architecture

This is the recommended order and where each piece runs.

## Architecture (best practice)

```
Phones ──Tailscale HTTPS──► Home OS Pi (192.168.1.254)
                              │ Flask + Postgres + nginx
                              │
              LAN REST API    │    LAN Moonraker :7125
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Home Assistant          K2 Plus
         (separate Pi preferred)   (Helper Script on printer)
         Govee, Ecobee, etc.
```

**Do not** put Home Assistant inside the Flask container. Home OS talks to HA over HTTP on your LAN — same pattern as the K2 printer.

| Component | Where it runs | Why |
|-----------|---------------|-----|
| Home OS Hub | Pi 400 (current) | Fitness + dashboard + API glue |
| Home Assistant | **Separate Pi** (ideal) or optional Docker on Pi 400 | Device hub — needs its own lifecycle |
| K2 Moonraker | On the printer | Already there |
| K2 Helper Script | **On the printer** | Unlocks camera bridge for Fluidd/Home OS |
| K2 camera bridge | On the printer (go2rtc) | Installed by Helper Script option 11 |

---

## 1. K2 camera — Helper Script (on the printer, not the Pi)

You do **not** write a script. This is a **community installer** maintained for Creality K2 printers.

### What it is

- [Creality Helper Script (K2 Plus wiki)](https://github.com/sw3defy/Creality-Helper-Script-Wiki-K2-Plus)
- Original project: [Guilouz Creality Helper Script](https://github.com/Guilouz/Creality-Helper-Script)

It adds tools to the printer's internal Linux (Fluidd, camera bridge, timelapse, etc.).

### Install camera support (option 11)

1. On your PC, open **Fluidd**: http://192.168.1.239:4408  
2. Open the **Terminal** (or SSH to the printer if enabled).
3. Run the helper menu (if already installed):
   ```bash
   sh /mnt/UDISK/helper-script/helper.sh
   ```
   If that path does not exist, follow the wiki **Install** section to download the helper first.
4. Choose **11) Camera Support for Fluidd and Mainsail**.
5. Reboot the printer. Wait ~60–90 seconds after boot.
6. Verify on the Pi:
   ```bash
   curl http://192.168.1.239:7125/server/webcams/list
   ```
   Should show a webcam entry (not empty `[]`).
7. Refresh **Home OS → Printer** — live camera appears automatically.

Until then, use the **Fluidd ↗** button on the printer panel for Creality's native camera UI.

---

## 2. K2 features in Home OS (done / timeline)

| Feature | Status | Notes |
|---------|--------|-------|
| Live status, pause/resume/cancel | ✅ Live | Moonraker |
| Preheat presets (PLA/PETG/ABS/cool down) | ✅ Live | Printer panel |
| Recent print history | ✅ Live | Moonraker `/server/history/list` |
| Embedded camera | ⏳ After Helper Script #11 | Auto-detected from Moonraker |
| Print-complete phone notification | Later | Needs HA or ntfy + automation |
| Timelapse | Later | Needs camera bridge first |

---

## 3. Home Assistant — recommended setup

### Option A — Separate Pi (recommended)

1. Flash **[Home Assistant OS](https://www.home-assistant.io/installation/raspberrypi)** onto a spare Pi (3/4/5 or mini PC).
2. Boot, create account at `http://<ha-ip>:8123`.
3. Add integrations in HA first (Govee, Ecobee, etc.) — devices live in HA, not Home OS.
4. In HA: **Profile → Security → Long-Lived Access Tokens** → create token.
5. Note entity IDs: **Settings → Devices & Services → entity** (e.g. `light.living_room`).
6. On the **Home OS Pi**:
   ```bash
   cd ~/HomeOS
   chmod +x scripts/configure-ha-env.sh
   ./scripts/configure-ha-env.sh \
     http://192.168.1.XX:8123 \
     eyJhbG...your-token... \
     light.living_room,light.bedroom \
     sensor.living_room_temperature
   ```
7. Open Home OS → **Home** panel — lights and sensor should be live (no mock badge).

Give HA a **static DHCP reservation** on your router so the IP does not change.

### Option B — HA container on the same Pi 400 (works, not ideal)

Only if you have **no spare Pi**. Your Pi has ~3.7 GB RAM — workable for Wi‑Fi/cloud devices, tight with heavy automations.

```bash
cd ~/HomeOS
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d
# First boot takes several minutes — watch logs:
docker compose -f docker-compose.yml -f docker-compose.ha.yml logs -f homeassistant
```

Then open `http://192.168.1.254:8123`, finish HA onboarding, create token, run `configure-ha-env.sh` with `http://192.168.1.254:8123` (or `http://homeassistant:8123` from inside Docker — use host IP for simplicity).

### Wiring summary

Home OS only needs four env vars (already supported in Flask):

```bash
HOME_ASSISTANT_URL=http://192.168.1.55:8123
HOME_ASSISTANT_TOKEN=eyJ...
HOME_ASSISTANT_LIGHTS=light.living_room,light.desk
HOME_ASSISTANT_SENSOR=sensor.living_room_temperature
```

Restart: `docker compose up -d`

---

## 4. Suggested order of operations

1. ✅ Home OS on Pi + Tailscale HTTPS  
2. ✅ K2 Moonraker wired  
3. **Helper Script camera (option 11)** on printer — ~15 min, you do this on printer terminal  
4. **Home Assistant** on spare Pi (or optional container) — ~30–60 min first setup  
5. **Add devices in HA** (Govee bulbs, thermostat, etc.)  
6. **Run `configure-ha-env.sh`** on Home OS Pi  
7. Later: print-done notifications via HA automation → mobile app  

---

## 5. What Home OS does vs HA

| Task | Use |
|------|-----|
| Gym logging, charts, PWA | Home OS |
| Quick light toggles on dashboard | Home OS (via HA API) |
| Adding new Zigbee/Wi‑Fi devices, automations, scenes | Home Assistant UI |
| Printer control at a glance | Home OS |
| Bed mesh, gcode upload, macros | Fluidd on printer |

Home OS is your **daily dashboard**; HA is the **device brain** behind it.
