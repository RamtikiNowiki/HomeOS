"""Database setup & seeding.

Idempotent: safe to run on every container boot. Creates all tables, both
user profiles, a default exercise library, and (optionally) demo history so
the UI looks alive on first load.

    python seed.py

Profiles are configured via environment variables (see .env.example):
    SEED_USER1_USERNAME / SEED_USER1_NAME / SEED_USER1_PASSWORD
    SEED_USER2_USERNAME / SEED_USER2_NAME / SEED_USER2_PASSWORD
    SEED_DEMO_DATA=1|0
"""
import os
import random
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Exercise, User, WeightLog, WorkoutSession, WorkoutSet, utcnow  # noqa: E402
from app.fitness.service import import_starter_library  # noqa: E402
from app.units import KG_TO_LB  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

DEFAULT_EXERCISES = [
    ("Bench Press", "Chest"),
    ("Squats", "Legs"),
    ("Pull-ups", "Back"),
    ("Overhead Press", "Shoulders"),
    ("Deadlift", "Back"),
]


def migrate_schema() -> None:
    """Add new columns to existing tables (create_all does not alter tables)."""
    inspector = inspect(db.engine)
    if "workout_sets" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("workout_sets")}
        if "rpe" not in columns:
            db.session.execute(text("ALTER TABLE workout_sets ADD COLUMN rpe FLOAT"))
            db.session.commit()
            print("  + migrated workout_sets.rpe column")
    if "workout_sessions" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("workout_sessions")}
        if "workout_type" not in columns:
            db.session.execute(text("ALTER TABLE workout_sessions ADD COLUMN workout_type VARCHAR(32)"))
            db.session.commit()
            print("  + migrated workout_sessions.workout_type column")
        if "routine_id" not in columns:
            db.session.execute(text("ALTER TABLE workout_sessions ADD COLUMN routine_id INTEGER"))
            db.session.commit()
            print("  + migrated workout_sessions.routine_id column")
        if "skipped_exercise_ids" not in columns:
            db.session.execute(text(
                "ALTER TABLE workout_sessions ADD COLUMN skipped_exercise_ids TEXT DEFAULT '[]' NOT NULL"
            ))
            db.session.commit()
            print("  + migrated workout_sessions.skipped_exercise_ids column")
        if "planned_exercise_ids" not in columns:
            db.session.execute(text(
                "ALTER TABLE workout_sessions ADD COLUMN planned_exercise_ids TEXT DEFAULT '[]' NOT NULL"
            ))
            db.session.commit()
            print("  + migrated workout_sessions.planned_exercise_ids column")
        if "use_split_template" not in columns:
            db.session.execute(text(
                "ALTER TABLE workout_sessions ADD COLUMN use_split_template BOOLEAN DEFAULT 0 NOT NULL"
            ))
            db.session.commit()
            print("  + migrated workout_sessions.use_split_template column")
    if "workout_sets" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("workout_sets")}
        if "is_warmup" not in columns:
            db.session.execute(text(
                "ALTER TABLE workout_sets ADD COLUMN is_warmup BOOLEAN DEFAULT 0 NOT NULL"
            ))
            db.session.commit()
            print("  + migrated workout_sets.is_warmup column")


def migrate_user1_to_indigo() -> None:
    """Ensure Ram's accent is the royal blue theme."""
    from app.models import User
    user1 = User.query.filter_by(username="ram").first()
    if user1 is not None and user1.accent != "indigo":
        user1.accent = "indigo"
        db.session.commit()
        print("  + migrated user1 (ram) → accent=indigo")


def seed_beginner_routines() -> None:
    """Create shared machine-friendly routines for Aylin if missing."""
    from app.models import User, WorkoutRoutine, WorkoutRoutineExercise, Exercise
    from app.fitness.catalog import BEGINNER_ROUTINES

    aylin = User.query.filter_by(username="aylin").first()
    if aylin is None:
        return
    import_beginner = __import__(
        "app.fitness.service", fromlist=["import_beginner_library"]
    ).import_beginner_library
    import_beginner(aylin.id)

    for spec in BEGINNER_ROUTINES:
        existing = WorkoutRoutine.query.filter_by(user_id=aylin.id, name=spec["name"]).first()
        if existing:
            continue
        routine = WorkoutRoutine(user_id=aylin.id, name=spec["name"])
        db.session.add(routine)
        db.session.flush()
        for i, ex_name in enumerate(spec["exercises"], start=1):
            ex = Exercise.query.filter_by(user_id=aylin.id, name=ex_name).first()
            if ex is None:
                continue
            db.session.add(
                WorkoutRoutineExercise(
                    routine_id=routine.id,
                    exercise_id=ex.id,
                    sort_order=i,
                )
            )
        print(f"  + created beginner routine “{spec['name']}” for Aylin")
    db.session.commit()


def migrate_user2_to_aylin() -> None:
    """Rename user2 (tiki/cyan) → Aylin/pink in the live DB."""
    from app.models import User  # local import to avoid circular at module level
    # Attempt both the old and new usernames so this is safe to re-run
    for old_username in ("tiki", "aylin"):
        user2 = User.query.filter_by(username=old_username).first()
        if user2 is None:
            continue
        changed = False
        if user2.display_name != "Aylin":
            user2.display_name = "Aylin"
            changed = True
        if user2.accent != "pink":
            user2.accent = "pink"
            changed = True
        if user2.username == "tiki":
            user2.username = "aylin"
            changed = True
        if changed:
            db.session.commit()
            print(f"  + migrated user2 → username=aylin, display_name=Aylin, accent=pink")
        break


def migrate_kg_to_lbs() -> None:
    """One-time conversion of legacy kg values to lb."""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if "workout_sets" not in tables:
        return

    if "app_meta" not in tables:
        db.session.execute(
            text("CREATE TABLE app_meta (key VARCHAR(64) PRIMARY KEY, value VARCHAR(64))")
        )
        db.session.commit()

    row = db.session.execute(
        text("SELECT value FROM app_meta WHERE key = 'weight_unit'")
    ).fetchone()
    if row is not None and row[0] == "lbs":
        return

    db.session.execute(
        text(f"UPDATE workout_sets SET weight = ROUND(weight * {KG_TO_LB}, 2) WHERE weight > 0")
    )
    if "weight_logs" in tables:
        db.session.execute(
            text(f"UPDATE weight_logs SET weight = ROUND(weight * {KG_TO_LB}, 1)")
        )

    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        db.session.execute(
            text("INSERT OR REPLACE INTO app_meta (key, value) VALUES ('weight_unit', 'lbs')")
        )
    else:
        db.session.execute(
            text(
                "INSERT INTO app_meta (key, value) VALUES ('weight_unit', 'lbs') "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            )
        )
    db.session.commit()
    print("  + migrated stored weights from kg to lb")


# Map legacy demo names to catalog names
_DEMO_LIFT_MAP = {
    "Bench Press": "Barbell Bench Press",
    "Squats": "Back Squat",
    "Pull-ups": "Pull-ups",
}

USER_SPECS = [
    {
        "username": os.environ.get("SEED_USER1_USERNAME", "ram"),
        "display_name": os.environ.get("SEED_USER1_NAME", "Ram"),
        "password": os.environ.get("SEED_USER1_PASSWORD", "changeme1"),
        "accent": "indigo",
        "start_weight": 181.0,
        "weight_drift": -0.3,
        "base_lifts": {"Bench Press": 135.0, "Squats": 185.0, "Pull-ups": 0.0},
    },
    {
        "username": os.environ.get("SEED_USER2_USERNAME", "aylin"),
        "display_name": os.environ.get("SEED_USER2_NAME", "Aylin"),
        "password": os.environ.get("SEED_USER2_PASSWORD", "changeme2"),
        "accent": "pink",
        "start_weight": 128.0,
        "weight_drift": -0.15,
        "base_lifts": {"Bench Press": 55.0, "Squats": 85.0, "Pull-ups": 0.0},
    },
]


def get_or_create_user(spec: dict) -> tuple[User, bool]:
    user = User.query.filter_by(username=spec["username"]).first()
    if user:
        return user, False
    user = User(
        username=spec["username"],
        display_name=spec["display_name"],
        accent=spec["accent"],
    )
    user.set_password(spec["password"])
    db.session.add(user)
    db.session.flush()
    print(f"  + created user @{user.username} ({user.display_name})")
    return user, True


def ensure_user_library(user: User) -> dict[str, Exercise]:
    added, _ = import_starter_library(user.id)
    if added:
        print(f"  + imported {added} catalog exercises for @{user.username}")
    return {ex.name: ex for ex in Exercise.query.filter_by(user_id=user.id).all()}


def seed_demo_history(user: User, spec: dict, exercises: dict[str, Exercise]) -> None:
    """Two finished sessions (showing progressive overload) + weight logs."""
    rng = random.Random(user.id)  # deterministic per user

    # --- Workout sessions: 8 and 3 days ago, with small progression ---
    session_plans = [
        ("Push Day", 8, 0.0),    # days ago, progression offset (lb)
        ("Full Body", 3, 5.0),
    ]
    for session_name, days_ago, progression in session_plans:
        started = utcnow() - timedelta(days=days_ago, hours=2)
        session = WorkoutSession(
            user_id=user.id,
            name=session_name,
            started_at=started,
            finished_at=started + timedelta(minutes=55),
        )
        db.session.add(session)
        db.session.flush()

        for exercise_name, base_weight in spec["base_lifts"].items():
            catalog_name = _DEMO_LIFT_MAP.get(exercise_name, exercise_name)
            exercise = exercises.get(catalog_name) or exercises.get(exercise_name)
            if exercise is None:
                continue
            weight = base_weight + progression if base_weight > 0 else 0.0
            for set_number in range(1, 4):
                reps = rng.choice([8, 8, 10]) if base_weight > 0 else rng.choice([5, 6, 8])
                db.session.add(
                    WorkoutSet(
                        session_id=session.id,
                        exercise_id=exercise.id,
                        set_number=set_number,
                        reps=reps,
                        weight=weight,
                        completed=True,
                    )
                )
        print(f"  + seeded session “{session_name}” for @{user.username}")

    # --- Weight logs: 10 entries over ~3 weeks ---
    weight = spec["start_weight"]
    for i in range(10, 0, -1):
        log_date = date.today() - timedelta(days=i * 2)
        weight += spec["weight_drift"] + rng.uniform(-0.25, 0.25)
        db.session.add(
            WeightLog(
                user_id=user.id,
                log_date=log_date,
                weight=round(weight, 1),
                body_fat=round(rng.uniform(17.0, 24.0), 1),
            )
        )
    print(f"  + seeded 10 weight logs for @{user.username}")


def main() -> None:
    app = create_app()
    with app.app_context():
        print("[seed] creating tables...")
        db.create_all()
        migrate_schema()
        migrate_user1_to_indigo()
        migrate_user2_to_aylin()
        migrate_kg_to_lbs()
        seed_beginner_routines()

        demo = os.environ.get("SEED_DEMO_DATA", "1") == "1"
        for spec in USER_SPECS:
            user, created = get_or_create_user(spec)
            exercises = ensure_user_library(user)
            if created and demo:
                seed_demo_history(user, spec, exercises)

        db.session.commit()
        print("[seed] done.")


if __name__ == "__main__":
    main()
