# Home OS & Fitness Hub — Project Reference

A self-hosted personal dashboard for two people, built to run on a **Raspberry Pi 400** (Docker) or locally on **Fedora** (SQLite). Combines workout tracking, body weight logging, smart home controls, and 3D printer monitoring in one mobile-first web app.

---

## What This Project Does

### Fitness (Workout Tab)

The fitness module is a **progressive overload workout tracker**. Each user has a completely isolated profile — exercises, sessions, sets, and weight logs never mix between users.

| Feature | Description |
|---------|-------------|
| **Exercise library** | Create, edit, and delete exercises with name and muscle group |
| **Workout sessions** | Start a named session, log sets, finish when done |
| **Set logging** | Record **weight (kg)**, **reps**, and optional **RPE** (6–10) per set |
| **Quick start** | Tap **+** on any exercise to auto-start a session and jump to logging |
| **Previous session targets** | Shows last session's sets so you know what to beat |
| **Set management** | Toggle completed, edit weight/reps/RPE, delete sets |
| **Session notes** | Add notes during or after a workout |
| **Training history** | Browse all completed sessions with expandable set details |
| **Personal records** | Stats page with estimated 1RM (Epley formula) per exercise |
| **Weekly summary** | Sessions and total volume lifted in the last 7 days |
| **Body weight log** | Manual weigh-ins with optional body fat % (VeSync-ready) |
| **Exercise catalog** | 55+ built-in exercises — browse, import by muscle group or workout type |
| **Workout splits** | Push, Pull, Legs, Chest, Back, Shoulders, Arms, Upper, Lower, Full Body |
| **Split-guided sessions** | Start a split → auto-import exercises → checklist with progress bar |
| **Rest timer** | Auto-starts after logging a set (60s–3m presets, phone vibrate) |

#### Typical workout flow

1. Open the **Workout** tab
2. **Start** a session (or tap **+** on an exercise for quick start)
3. Pick an exercise → log sets: weight × reps (optional RPE)
4. Add more exercises as needed
5. **Finish** the session when done
6. View history, stats, and PRs anytime

### Dashboard

Aggregated widgets for the logged-in user:

- Active workout banner (resume in-progress session)
- Body weight trend with sparkline
- Last workout summary
- Smart home lights + temperature sensor
- Creality K2 Plus print status

### Smart Home (Home Tab)

Home Assistant integration panel. Runs in **mock mode** until `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN` are configured.

### 3D Printer (Printer Tab)

Creality K2 Plus monitoring via Moonraker API. Runs in **mock mode** until `CREALITY_K2_HOST` is configured.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.1 (application factory + blueprints) |
| Auth | Flask-Login (session cookies, remember-me) |
| Database | SQLAlchemy 2.0 / Flask-SQLAlchemy |
| DB (local dev) | SQLite → `instance/dev.db` |
| DB (production) | PostgreSQL 16 via Docker |
| Frontend | Jinja2 templates, Tailwind CSS (CDN), vanilla JS |
| Server (prod) | Gunicorn behind nginx |
| Deployment | Docker Compose (web + db + nginx), multi-arch (x86 / arm64) |

---

## Project Structure

```
home-os-hub/
├── app/
│   ├── __init__.py           # Application factory, blueprint registration
│   ├── extensions.py         # db, login_manager
│   ├── models.py             # User, Exercise, WorkoutSession, WorkoutSet, WeightLog
│   ├── auth/                 # Login, logout, profile switching
│   ├── main/                 # Dashboard
│   ├── fitness/              # Workout tracking (routes.py)
│   ├── home_assistant/       # HA panel + service.py
│   ├── creality_k2/          # Printer panel + service.py
│   ├── templates/            # Jinja HTML templates
│   └── static/               # CSS + JS
├── config.py                 # Dev/prod configuration
├── wsgi.py                   # App entry point
├── seed.py                   # DB setup + user/exercise seeding
├── Dockerfile
├── docker-compose.yml
├── nginx/nginx.conf
├── .env.example
├── README.md                 # Quick start guide
└── PROJECT.md                # This file — full project reference
```

---

## Data Model

All fitness data is scoped by `user_id`.

```
User
 ├── Exercise (name, muscle_group)
 │    └── WorkoutSet (weight, reps, rpe, completed, set_number)
 ├── WorkoutSession (name, started_at, finished_at, notes)
 │    └── WorkoutSet
 └── WeightLog (log_date, weight, body_fat)
```

### Key concepts

- **One active session per user** — starting a new session redirects to the existing one if still open
- **Volume** — sum of `weight × reps` for completed sets in a session
- **Personal record** — best set by estimated 1RM: `weight × (1 + reps/30)` (Epley)
- **Previous session target** — full set list from the last session containing that exercise

---

## Routes Reference

### Fitness (`/fitness`)

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/` | Workout hub — start session, exercise list, quick actions |
| POST | `/session/start` | Start a new workout session |
| GET | `/session/<id>` | Session detail — exercises performed, picker |
| POST | `/session/<id>/finish` | Finish session (discards if empty) |
| POST | `/session/<id>/notes` | Save session notes |
| POST | `/session/<id>/delete` | Delete a session and all its sets |
| GET | `/session/<id>/exercise/<id>` | Log sets for an exercise |
| POST | `/session/<id>/exercise/<id>/sets` | Add a set |
| POST | `/exercise/<id>/quick-start` | Auto-start session + go to exercise |
| POST | `/sets/<id>/toggle` | Toggle set completed (JSON) |
| POST | `/sets/<id>/edit` | Update set weight/reps/RPE |
| POST | `/sets/<id>/delete` | Delete set and renumber |
| GET | `/exercises` | Exercise library management |
| POST | `/exercises` | Create exercise |
| POST | `/exercises/<id>/edit` | Update exercise |
| POST | `/exercises/<id>/delete` | Delete exercise |
| GET | `/catalog` | Browse built-in exercise catalog |
| POST | `/catalog/add` | Add one catalog exercise to library |
| POST | `/catalog/import-starter` | Import full starter library |
| POST | `/catalog/import-split` | Import exercises for a workout type |
| GET | `/stats` | Personal records + weekly summary |
| GET | `/history` | Completed session history |
| GET/POST | `/weight` | Body weight log |
| POST | `/weight/<id>/delete` | Delete weight entry |

### Other modules

| Prefix | Module |
|--------|--------|
| `/` | Dashboard |
| `/login` | Authentication |
| `/home` | Smart home panel |
| `/printer` | 3D printer panel |

---

## Local Development (Fedora)

No PostgreSQL required — SQLite is used automatically.

```bash
cd home-os-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional: customize usernames/passwords
python seed.py                # creates tables, profiles, demo data
python wsgi.py                # http://localhost:5000
```

### Access from your phone (same Wi‑Fi)

The dev server binds to all interfaces (`0.0.0.0:5000`). On startup it prints your LAN URL, e.g. `http://192.168.233.62:5000`.

1. PC and phone must be on the **same Wi‑Fi network**
2. Use your PC's LAN IP (not `localhost`) — find it with `ip addr` or read the startup message
3. If the page won't load on Fedora, allow port 5000 through the firewall:

```bash
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

On the Pi (Docker), use `http://<pi-ip>/` on port 80 instead.

### Default logins

| Profile | Username | Password |
|---------|----------|----------|
| User 1  | `ram`    | `changeme1` |
| User 2  | `tiki`   | `changeme2` |

Override via `.env` **before** running `seed.py`:

```
SEED_USER1_USERNAME=ram
SEED_USER1_NAME=Ram
SEED_USER1_PASSWORD=changeme1
SEED_USER2_USERNAME=tiki
SEED_USER2_NAME=Tiki
SEED_USER2_PASSWORD=changeme2
SEED_DEMO_DATA=1              # set to 0 for clean profiles
```

### Schema updates

There is no Alembic migration system. `seed.py` runs `db.create_all()` plus a lightweight column migration for new fields. After pulling model changes:

```bash
python seed.py
```

If a column change fails on an old SQLite file, delete `instance/dev.db` and re-seed.

---

## Production Deployment (Raspberry Pi 400)

```bash
git clone <repo> && cd home-os-hub
cp .env.example .env
nano .env                     # SECRET_KEY, POSTGRES_PASSWORD, profile passwords
docker compose up -d --build
```

- App available at `http://<pi-ip>/` (nginx on port 80)
- Postgres data persists in the `pgdata` Docker volume
- Entrypoint waits for DB, runs `seed.py`, starts Gunicorn
- Set `SEED_DEMO_DATA=0` before first boot for empty profiles

```bash
docker compose logs -f web    # view logs
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Prod | Flask session signing |
| `DATABASE_URL` | Prod | PostgreSQL connection string |
| `POSTGRES_PASSWORD` | Docker | Postgres password |
| `SEED_USER*_USERNAME/NAME/PASSWORD` | Docker | Profile credentials |
| `SEED_DEMO_DATA` | No | `1` = seed demo workouts (default) |
| `HOME_ASSISTANT_URL` | No | HA base URL |
| `HOME_ASSISTANT_TOKEN` | No | HA long-lived token |
| `CREALITY_K2_HOST` | No | Moonraker API host |

---

## Future Integrations

| Integration | Status | Where to implement |
|-------------|--------|-------------------|
| VeSync smart scale | Model ready (`WeightLog`) | Add `fitness/service.py` sync |
| Home Assistant | Mock mode | `app/home_assistant/service.py` |
| Creality K2 Plus | Mock mode | `app/creality_k2/service.py` |

Each integration service uses an `is_mock` property — the UI shows a badge until real credentials are configured.

---

## Design Conventions

- **Dark "home lab" theme** — void/panel/raised colors, Chakra Petch + Inter fonts
- **Mobile-first** — bottom nav with 4 tabs, touch-friendly 44px targets
- **Per-user accent** — indigo (User 1) or cyan (User 2)
- **Flash toasts** — success/error feedback after form actions
- **PRG pattern** — POST → redirect → GET for form submissions
- **Ownership guards** — every fitness query filtered by `current_user.id`

---

## Seeded Demo Data

When `SEED_DEMO_DATA=1` (default), new users get:

- 5 default exercises: Bench Press, Squats, Pull-ups, Overhead Press, Deadlift
- 2 finished workout sessions (8 and 3 days ago) with progressive overload
- 10 weight log entries over ~3 weeks

This makes the dashboard and stats pages useful immediately after first login.
