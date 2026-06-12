# Home OS & Fitness Hub

A self-hosted, mobile-first dashboard for two people: progressive-overload workout tracking, weight logging (VeSync-ready), smart home controls (Home Assistant-ready), and Creality K2 Plus print monitoring. Dark "home lab" aesthetic, built to run on a Raspberry Pi 400 behind nginx.

## Stack

- **Backend:** Flask (application factory + blueprints), Flask-Login, SQLAlchemy
- **Database:** PostgreSQL in production, SQLite fallback for local dev
- **Frontend:** Jinja templates + Tailwind CSS (CDN), vanilla JS, persistent bottom nav
- **Deployment:** Docker Compose (web + db + nginx), multi-arch images (x86 / arm64)

## Project layout

```
home-os-hub/
├── app/
│   ├── __init__.py            # application factory
│   ├── extensions.py          # db, login_manager
│   ├── models.py              # User, Exercise, WorkoutSession, WorkoutSet, WeightLog
│   ├── auth/                  # login / logout / profile switching
│   ├── main/                  # dashboard widgets
│   ├── fitness/               # sessions, sets, weight logs, history
│   ├── home_assistant/        # HA panel + service class (mock mode)
│   ├── creality_k2/           # printer panel + service class (mock mode)
│   ├── templates/
│   └── static/
├── config.py
├── wsgi.py
├── seed.py                    # idempotent table creation + profile/demo seeding
├── Dockerfile                 # multi-stage production build
├── docker/entrypoint.sh       # waits for db, seeds, starts gunicorn
├── nginx/nginx.conf           # reverse proxy
├── docker-compose.yml
├── .env.example
├── README.md                 # Quick start guide
└── PROJECT.md                # Full project reference (features, routes, data model)
```

## Local development (Fedora)

No Postgres needed — the app falls back to SQLite at `instance/dev.db`.

```bash
cd home-os-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional: customize usernames/passwords
python seed.py                # creates tables, both profiles, demo data
python wsgi.py                # serves on http://localhost:5000
```

**Phone on same Wi‑Fi:** use `http://<your-pc-ip>:5000` (printed when the server starts). If blocked on Fedora: `sudo firewall-cmd --add-port=5000/tcp --permanent && sudo firewall-cmd --reload`

Default dev logins (override via `.env` before seeding):

| Profile | Username | Password    |
|---------|----------|-------------|
| User 1  | `ram`    | `changeme1` |
| User 2  | `tiki`   | `changeme2` |

## Production deployment (Raspberry Pi 400)

```bash
git clone <this repo> && cd home-os-hub
cp .env.example .env
nano .env                     # set SECRET_KEY, POSTGRES_PASSWORD, profile passcodes
docker compose up -d --build
```

That's it. The entrypoint waits for Postgres, runs the idempotent seed (creating both profiles on first boot), and starts gunicorn. nginx serves the app on port 80 — open `http://<pi-address>/`.

- Postgres data persists in the `pgdata` named volume.
- Set `SEED_DEMO_DATA=0` in `.env` before first boot if you want clean profiles with no dummy history.
- Logs: `docker compose logs -f web`

## Wiring up the real integrations later

| Integration   | Env vars                                    | Where to implement                      |
|---------------|---------------------------------------------|-----------------------------------------|
| Home Assistant| `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`| `app/home_assistant/service.py`          |
| Creality K2   | `CREALITY_K2_HOST` (Moonraker API)          | `app/creality_k2/service.py`             |
| VeSync scale  | —                                           | write into the existing `WeightLog` model|

Each service class has an `is_mock` property — the UI shows a "Mock Mode" badge until real credentials are configured, and the mock branches are clearly marked for replacement.
