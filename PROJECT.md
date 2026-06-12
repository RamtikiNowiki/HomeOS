# Home OS & Fitness Hub — Project Reference

A self-hosted personal dashboard for **two people** (Ram & Aylin), built to run on a **Raspberry Pi 400** (Docker) or locally on **Fedora** (SQLite). Combines workout tracking, body weight logging, smart home controls, and 3D printer monitoring in one mobile-first web app.

Use this file as the canonical reference when prompting agents or onboarding to the codebase.

---

## Users & Theming

| Profile | Default username | Accent | Pixel theme | Default UI theme |
|---------|------------------|--------|-------------|------------------|
| Ram | `ram` | `indigo` | Blue (muscular male character) | Dark |
| Aylin | `aylin` | `pink` | Pink (chibi female character) | Light |

- Each user has **fully isolated** fitness data (`user_id` on every row).
- `User.accent` drives CSS variables, login avatar, and `px_theme` (`pink` or `blue`).
- Legacy DBs may still have `tiki` / `cyan` — `seed.py` migrates user2 → `aylin` / `pink`.
- Login page sets `localStorage.theme` from accent before entering the app.

---

## What This Project Does

### Fitness (Workout tab)

Progressive-overload workout tracker with in-gym UX (large tap targets, rest timer, AJAX set logging, offline Tailwind).

#### Navigation (`_subnav.html`)

Four persistent tabs inside `/fitness`:

| Tab | Route | Purpose |
|-----|-------|---------|
| **Train** / **Resume** | `/fitness/` | Start sessions, exercise list, active workout UI |
| **History** | `/fitness/history` | Completed sessions, CSV export |
| **Stats** | `/fitness/stats` | PRs (Epley 1RM), weekly volume |
| **Tools** | `/fitness/tools` | Planning, catalog, charts, weight, plates |

`fitness.nav.workout_entry_url()` resumes the smart URL: next planned exercise → last logged → session detail.

#### Train (`/fitness/`)

| Feature | Description |
|---------|-------------|
| **Start session** | Named session from split, saved routine, weekly program, blank quick-start, or repeat last |
| **Active session UI** | Live stats, plan checklist, workout switch panel, discard/finish |
| **Exercise list** | Pixel icons, friendly display names, search + muscle filter + **Machines only** toggle |
| **Quick start** | Tap **+** on any exercise → auto-start/resume session → log screen |
| **Workout streaks** | Weekly session count + consecutive-day streak (when no active session) |
| **Custom exercises** | Inline form to add name + muscle group |

#### Set logging (`log_exercise.html` + `fitness.js`)

| Feature | Description |
|---------|-------------|
| **Set logging** | Weight (**lb**), reps, optional RPE (6–10), warmup flag |
| **AJAX add set** | No full page reload; haptic feedback on mobile |
| **Previous session target** | Full prior set list + top set to beat |
| **Rest timer** | Auto-starts after log; presets 60s–3m; **next exercise** hint with icon |
| **Sound + haptics** | Optional rest-end beep (`localStorage`); vibrate on timer done |
| **Plate calculator link** | Barbell exercises link to `/fitness/plates?weight=` (updates live) |
| **PR celebration** | Overlay when `check_set_beats_pr()` detects a new best |
| **Plan tray** | Collapsible chips for planned exercises (icons + display names) |
| **Skip / unskip** | Machine taken? Skip planned exercise and restore later |
| **On-the-fly plan edits** | Add/remove exercises from active session plan |

#### Tools & planning

| Feature | Description |
|---------|-------------|
| **Exercise catalog** | 98 built-in lifts in `catalog.py` — browse, import one, starter pack, beginner pack, by split |
| **Beginner mode** | 41 machine/bodyweight-friendly exercises; filter in pickers; Aylin starter routines |
| **Workout splits** | 10 templates: Push, Pull, Legs, Chest, Back, Shoulders, Arms, Upper, Lower, Full Body |
| **Plan workout** | Build/edit a session plan before starting (`/fitness/plan`) |
| **Saved routines** | Reusable plans with target sets/reps — preview, edit, one-tap start |
| **Weekly program** | Assign split or routine to each weekday; **Start Today** button |
| **Progress charts** | Body weight, weekly volume, per-exercise estimated 1RM, recent PR events |
| **Body weight log** | Manual weigh-ins + optional body fat % (VeSync-ready model) |
| **Plate calculator** | US standard plates per side; accepts `?weight=` on GET |
| **History export** | `/fitness/history/export.csv` |

#### Typical workout flow

1. Open **Train** (or resume from dashboard / bottom nav)
2. Start from split, routine, program, blank session, or tap **+** on an exercise
3. Log sets: weight × reps (optional RPE) — rest timer runs automatically
4. Skip, switch, or add exercises as needed
5. **Finish** session → appears in History and Stats
6. Review PRs, charts, streaks anytime

### Dashboard (`/`)

Aggregated widgets for the logged-in user:

- Greeting + **workout streak** (week / day)
- **Today's program** banner (from weekly program, links to plan/routine)
- **Active workout** banner with resume, stats, discard
- Body weight trend + sparkline
- Last finished workout summary
- Smart home lights + temperature (mock or live)
- Creality K2 Plus print status (mock or live)

### Smart Home (`/home`)

Home Assistant integration panel. **Mock mode** until `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN` are set. Toggle lights, read temp/humidity sensor.

### 3D Printer (`/printer`)

Creality K2 Plus via Moonraker API. **Mock mode** until `CREALITY_K2_HOST` is set. Live progress bar, temps, layer count, filament used.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.1 (application factory + blueprints) |
| Auth | Flask-Login (session cookies, remember-me) |
| Database | SQLAlchemy 2.0 / Flask-SQLAlchemy |
| DB (local dev) | SQLite → `instance/dev.db` |
| DB (production) | PostgreSQL 16 via Docker |
| Frontend | Jinja2 templates, **Tailwind CSS (bundled locally)**, vanilla JS |
| Fonts | Chakra Petch (display) + Inter (body) |
| Server (prod) | Gunicorn behind nginx |
| Deployment | Docker Compose (web + db + nginx), multi-arch (x86 / arm64) |

**No Alembic** — schema changes use `db.create_all()` + manual `ALTER TABLE` in `seed.py` (`migrate_schema()`).

---

## Project Structure

```
home-os-hub/
├── app/
│   ├── __init__.py              # Factory, template filters, context processors
│   ├── extensions.py            # db, login_manager
│   ├── models.py                # All SQLAlchemy models
│   ├── units.py                 # lb formatting (values stored in lb)
│   ├── auth/                    # Login, logout
│   ├── main/                    # Dashboard
│   ├── fitness/
│   │   ├── routes.py            # Core workout routes
│   │   ├── routes_extra.py      # Routines, program, charts, plates, plan
│   │   ├── service.py           # Import, PR check, streaks, session helpers
│   │   ├── catalog.py           # 98-exercise catalog, splits, icons, beginner metadata
│   │   ├── nav.py               # Tab state, smart resume URLs
│   │   ├── plates.py            # Plate math
│   │   └── charts_data.py       # Chart JSON builders
│   ├── home_assistant/          # HA panel + service.py
│   ├── creality_k2/             # Printer panel + service.py
│   ├── templates/
│   │   ├── base.html            # Theme boot, bottom nav, Tailwind config
│   │   ├── dashboard.html
│   │   ├── auth/login.html      # Profile picker + pixel avatars
│   │   └── fitness/             # 21 templates + partials (_subnav, _breadcrumb, …)
│   └── static/
│       ├── css/app.css          # Theme vars, animations, pixel icons
│       ├── js/
│       │   ├── fitness.js       # Picker, log sheet, rest timer, PR, AJAX sets
│       │   ├── plan.js          # Plan builder preview
│       │   ├── app.js           # HA light toggles, printer polling
│       │   └── tailwind.min.js  # Offline Tailwind (~407 KB)
│       └── img/px/
│           ├── pink/            # 19 movement/equipment icons (Aylin)
│           └── blue/            # 19 matching icons (Ram)
├── config.py
├── wsgi.py                      # Dev server (0.0.0.0:5000, prints LAN URL)
├── seed.py                      # Tables, migrations, users, demo data, Aylin routines
├── tests/
│   ├── smoke_test.py            # Runs without pytest
│   ├── test_catalog.py
│   └── test_service.py
├── Dockerfile
├── docker-compose.yml
├── nginx/nginx.conf
├── .env.example
├── README.md                    # Quick start
└── PROJECT.md                   # This file
```

---

## Data Model

All fitness data scoped by `user_id`. Weights stored in **pounds (lb)**.

```
User (username, display_name, accent, password_hash)
 ├── Exercise (name, muscle_group)           — unique per user
 │    └── WorkoutSet (weight, reps, rpe, completed, is_warmup, set_number)
 ├── WorkoutSession (name, workout_type, started_at, finished_at, notes)
 │    ├── use_split_template, routine_id
 │    ├── planned_exercise_ids (JSON list)
 │    ├── skipped_exercise_ids (JSON list)
 │    └── WorkoutSet
 ├── WorkoutRoutine (name, split_key)
 │    └── WorkoutRoutineExercise (exercise_id, sort_order, target_sets, target_reps)
 ├── UserProgramDay (day_of_week 0=Mon…6=Sun, split_key OR routine_id)
 └── WeightLog (log_date, weight, body_fat)
```

### Key concepts

- **One active session per user** — starting redirects to existing open session
- **Volume** — Σ `weight × reps` for completed, non-warmup sets
- **Personal record** — best working set by Epley 1RM: `weight × (1 + reps/30)`
- **Previous session target** — all sets from the most recent prior session containing that exercise
- **Planned queue** — `planned_exercise_ids` drives checklist + tray; split/routine sessions populate on start
- **Warmup sets** — excluded from volume, PR checks, and completion stats

---

## Exercise Catalog (`app/fitness/catalog.py`)

| Constant | Count | Purpose |
|----------|-------|---------|
| `EXERCISE_CATALOG` | 98 | Built-in lifts with muscle group + equipment |
| `WORKOUT_SPLITS` | 10 | Named templates with exercise lists |
| `BEGINNER_EXERCISES` | 41 | Machine/bodyweight-friendly subset |
| `BEGINNER_ROUTINES` | 2 | “Aylin — Easy Leg Day”, “Aylin — Upper Machines” |
| `STARTER_EXERCISES` | ~55 | Default import on new user |

**Display layer** (catalog name → UI):

- `CATALOG_DISPLAY_NAMES` — friendly labels (e.g. “Leg Press” → “Leg Press (sled)”)
- `CATALOG_ALIASES` — search synonyms
- `CATALOG_ICON_OVERRIDES` — force specific pixel slug
- `icon_slug_for_exercise()` — override → keyword match → muscle default → equipment fallback

**Pixel icon slugs** (19 PNGs per theme): `squat`, `deadlift`, `bench-press`, `overhead-press`, `row`, `pullup`, `leg-press`, `lunge`, `curl`, `lateral-raise`, `triceps`, `core`, `barbell`, `dumbbell`, `kettlebell`, `cable`, `machine`, `bodyweight`, `empty-state`

### Jinja filters (`app/__init__.py`)

| Filter | Purpose |
|--------|---------|
| `lbs` / `kg` | Format weight (both — values are lb) |
| `num` | Format numbers for display |
| `ex_icon` | Themed pixel icon path for an exercise |
| `ex_display` | Friendly display name |
| `ex_beginner` | Whether exercise is beginner-friendly |
| `ex_search` | Lowercase search blob (name + aliases + muscle) |

### Context processors

- `px_theme`, `theme_color_light/dark`, `default_theme` — per-user browser chrome
- `has_active_workout`, `active_workout`, `fitness_workout_url`, `fitness_tab` — nav state

---

## Routes Reference

### Fitness — core (`routes.py`)

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/fitness/` | Train hub |
| GET | `/fitness/tools` | Tools landing page |
| POST | `/fitness/session/start` | Start session (split / routine / blank) |
| GET | `/fitness/session/<id>` | Session detail + exercise picker |
| POST | `/fitness/session/<id>/finish` | Finish (discard if empty) |
| POST | `/fitness/session/<id>/discard` | Abandon active session |
| POST | `/fitness/session/<id>/notes` | Save notes (JSON or form) |
| POST | `/fitness/session/<id>/delete` | Delete session + sets |
| POST | `/fitness/session/<id>/plan/add/<ex_id>` | Add to on-the-fly plan |
| POST | `/fitness/session/<id>/plan/remove/<ex_id>` | Remove from plan |
| POST | `/fitness/session/<id>/skip/<ex_id>` | Skip planned exercise |
| POST | `/fitness/session/<id>/unskip/<ex_id>` | Restore skipped exercise |
| GET | `/fitness/session/<id>/exercise/<ex_id>` | Log sets UI |
| POST | `/fitness/session/<id>/exercise/<ex_id>/sets` | Add set (JSON or redirect) |
| POST | `/fitness/exercise/<id>/quick-start` | Auto-start + jump to log |
| POST | `/fitness/sets/<id>/toggle` | Toggle completed (JSON) |
| POST | `/fitness/sets/<id>/edit` | Update weight/reps/RPE |
| POST | `/fitness/sets/<id>/delete` | Delete + renumber |
| GET | `/fitness/exercises/search` | JSON search for pickers |
| GET/POST | `/fitness/exercises` | Manage library |
| POST | `/fitness/exercises/<id>/edit` | Update exercise |
| POST | `/fitness/exercises/<id>/delete` | Delete exercise |
| GET | `/fitness/catalog` | Browse catalog |
| POST | `/fitness/catalog/add` | Import one exercise |
| POST | `/fitness/catalog/import-starter` | Import starter library |
| POST | `/fitness/catalog/import-beginner` | Import beginner exercises |
| POST | `/fitness/catalog/import-split` | Import split exercises |
| GET | `/fitness/stats` | PRs + weekly summary |
| GET | `/fitness/history` | Completed sessions |
| GET | `/fitness/history/export.csv` | CSV export |
| GET/POST | `/fitness/weight` | Body weight log |
| POST | `/fitness/weight/<id>/delete` | Delete weigh-in |

### Fitness — planning & utilities (`routes_extra.py`)

| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/fitness/session/repeat-last` | Clone last finished session |
| POST | `/fitness/session/<id>/repeat` | Repeat a specific session |
| POST | `/fitness/session/<id>/save-routine` | Save session as routine |
| GET/POST | `/fitness/plan` | Plan builder (optional `?split=` or routine edit) |
| GET | `/fitness/routines` | Saved routines list |
| GET/POST | `/fitness/routines/new` | Create routine |
| GET/POST | `/fitness/routines/<id>/edit` | Edit routine |
| GET | `/fitness/routines/<id>` | Routine preview |
| POST | `/fitness/routines/quick` | Quick-save from session |
| POST | `/fitness/routines/<id>/delete` | Delete routine |
| POST | `/fitness/routines/<id>/start` | Start session from routine |
| GET/POST | `/fitness/program` | Weekly program editor |
| POST | `/fitness/program/start-today` | Start today's assigned workout |
| GET | `/fitness/charts` | Progress charts (Chart.js) |
| GET/POST | `/fitness/plates` | Plate calculator |

### Other modules

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/` | `main` | Dashboard |
| `/login`, `/logout` | `auth` | Profile picker + passcode |
| `/home` | `home_assistant` | Smart home panel |
| `/printer` | `creality_k2` | 3D printer panel |

---

## Frontend JS (`fitness.js`)

| Function | Purpose |
|----------|---------|
| `initExercisePicker()` | Search, muscle chips/select, beginner toggle (`localStorage: fitness-beginner-mode`) |
| `initLogSheet()` | Collapsible log sheet on session/log pages |
| `initAjaxSetLogging()` | POST sets via fetch, update DOM, trigger rest timer |
| `initRestTimer()` | Countdown, next-exercise hint, sound/haptics |
| `initSwitchPanel()` | Workout switch overlay during active session |
| `initPlanAjax()` | Live plan tray updates |
| `initConfirmForms()` | `data-confirm` delete/discard prompts |

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

### Tests

```bash
python tests/smoke_test.py              # no pytest needed
# pip install pytest && pytest tests/   # full suite (optional)
```

### Access from phone (same Wi‑Fi)

Dev server binds `0.0.0.0:5000` and prints the LAN URL on startup.

```bash
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

On the Pi (Docker), use `http://<pi-ip>/` on port 80.

### Default logins

| Profile | Username | Password |
|---------|----------|----------|
| Ram | `ram` | `changeme1` |
| Aylin | `aylin` | `changeme2` |

Override via `.env` **before** first `seed.py`:

```
SEED_USER1_USERNAME=ram
SEED_USER1_NAME=Ram
SEED_USER1_PASSWORD=changeme1
SEED_USER2_USERNAME=aylin
SEED_USER2_NAME=Aylin
SEED_USER2_PASSWORD=changeme2
SEED_DEMO_DATA=1              # 0 = clean profiles (no demo sessions/weights)
```

### Schema updates

After pulling model changes:

```bash
python seed.py
```

If a column migration fails on old SQLite, delete `instance/dev.db` and re-seed.

`seed.py` also runs:

- `migrate_schema()` — additive column patches
- `migrate_user1_to_indigo()` / `migrate_user2_to_aylin()` — accent/username fixes
- `migrate_kg_to_lbs()` — one-time kg → lb conversion (tracked in `app_meta`)
- `seed_beginner_routines()` — Aylin machine routines if missing

---

## Production Deployment (Raspberry Pi 400)

```bash
git clone <repo> && cd home-os-hub
cp .env.example .env
nano .env                     # SECRET_KEY, POSTGRES_PASSWORD, profile passwords
docker compose up -d --build
```

- App at `http://<pi-ip>/` (nginx port 80)
- Postgres persists in `pgdata` volume
- Entrypoint waits for DB, runs `seed.py`, starts Gunicorn
- Set `SEED_DEMO_DATA=0` before first boot for empty profiles

```bash
docker compose logs -f web
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Prod | Flask session signing |
| `DATABASE_URL` | Prod | PostgreSQL connection string |
| `POSTGRES_PASSWORD` | Docker | Postgres password |
| `SEED_USER*_USERNAME/NAME/PASSWORD` | No | Profile credentials (defaults above) |
| `SEED_DEMO_DATA` | No | `1` = demo sessions/weights on first create (default) |
| `HOME_ASSISTANT_URL` | No | HA base URL |
| `HOME_ASSISTANT_TOKEN` | No | HA long-lived token |
| `CREALITY_K2_HOST` | No | Moonraker API host |

---

## Seeded Demo Data

When `SEED_DEMO_DATA=1` and a user is **newly created**:

- Full **starter catalog** imported (~55 exercises)
- 2 finished sessions (8 and 3 days ago) with progressive overload
- 10 body-weight log entries over ~3 weeks

Always (idempotent):

- Both user profiles created if missing
- Aylin gets **beginner exercises** + **starter routines** (“Easy Leg Day”, “Upper Machines”)

---

## Design Conventions

- **Dark “home lab” theme** — CSS vars `--void`, `--panel`, `--raised`, `--edge`, `--neon`, `--pulse`
- **Light mode** — toggled via header button; persisted in `localStorage.theme`
- **Mobile-first** — bottom nav (Dashboard, Workout, Home, Printer), 44px+ tap targets
- **Per-user accent** — indigo/pulse (Ram), pink/neon (Aylin)
- **Template partials** — `_page_header`, `_section_header`, `_breadcrumb`, `_subnav`, `_workout_switch`
- **Flash toasts** — success/error after form actions
- **PRG pattern** — POST → redirect → GET (JSON endpoints for AJAX set logging)
- **Ownership guards** — `_get_own_session()`, `_get_own_exercise()`; every query filters `current_user.id`
- **Pixel icons** — `.pixel-icon` class; themed via `px_theme` context var

---

## Future / Not Yet Implemented

| Item | Status | Notes |
|------|--------|-------|
| VeSync smart scale sync | Model ready | `WeightLog` exists; no API sync yet |
| Home Assistant | Mock mode | `app/home_assistant/service.py` |
| Creality K2 Plus | Mock mode | `app/creality_k2/service.py` |
| DB backup automation | Not planned | Explicitly deferred |
| Alembic migrations | Not used | Manual patches in `seed.py` |
| Per-exercise unique art | Partial | 19 movement icons cover all 98 via mapping |
| pytest in CI | Optional | `tests/` exist; run locally with `pip install pytest` |

Integration services expose `is_mock` — UI shows a badge until real credentials are configured.

---

## Quick Agent Checklist

When modifying fitness features, check:

1. **User scoping** — filter by `current_user.id`; never import `current_user` locally inside a function that uses it earlier (causes `UnboundLocalError`)
2. **Weight unit** — store/display lb; use `|lbs` filter
3. **Catalog changes** — update `catalog.py`, consider `BEGINNER_EXERCISES`, icon slug mapping
4. **New routes** — add to `fitness.nav._TOOLS_ENDPOINTS` if Tools tab should highlight
5. **Schema changes** — add migration in `seed.py` `migrate_schema()`
6. **Offline/Pi** — avoid CDN dependencies; Tailwind is bundled at `static/js/tailwind.min.js`
7. **Both themes** — test pink + blue pixel icons if touching exercise UI
