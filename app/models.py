"""SQLAlchemy models.

Every fitness-related row is scoped to a user_id so the two profiles never
share data. The workout schema is built for progressive overload:

    Exercise -> WorkoutSession -> WorkoutSet (reps / weight / completed)
"""
import json
from datetime import datetime, date, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow() -> datetime:
    """Naive UTC timestamp (columns store naive UTC consistently)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(64), nullable=False)
    accent = db.Column(db.String(16), nullable=False, default="indigo")  # indigo | cyan | pink
    password_hash = db.Column(db.String(256), nullable=False)
    preferences_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    exercises = db.relationship("Exercise", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    sessions = db.relationship("WorkoutSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    weight_logs = db.relationship("WeightLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    routines = db.relationship("WorkoutRoutine", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    program_days = db.relationship("UserProgramDay", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_preferences(self) -> dict:
        try:
            data = json.loads(self.preferences_json or "{}")
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_preferences(self, updates: dict) -> None:
        prefs = self.get_preferences()
        prefs.update(updates)
        self.preferences_json = json.dumps(prefs)

    def get_pref(self, key: str, default=None):
        return self.get_preferences().get(key, default)

    @property
    def initial(self) -> str:
        return self.display_name[:1].upper()

    def __repr__(self):
        return f"<User {self.username}>"


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    muscle_group = db.Column(db.String(64), nullable=False, default="General")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    sets = db.relationship("WorkoutSet", backref="exercise", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_exercise_user_name"),)

    def personal_record(self) -> dict | None:
        """Best completed working set by estimated 1RM (Epley formula)."""
        sets = (
            WorkoutSet.query.join(WorkoutSession)
            .filter(
                WorkoutSession.user_id == self.user_id,
                WorkoutSet.exercise_id == self.id,
                WorkoutSet.completed.is_(True),
                WorkoutSet.is_warmup.is_(False),
            )
            .all()
        )
        if not sets:
            return None
        best = max(sets, key=lambda s: s.estimated_1rm)
        return {
            "weight": best.weight,
            "reps": best.reps,
            "estimated_1rm": best.estimated_1rm,
            "date": best.session.started_at,
        }

    def last_completed_session_sets(self, exclude_session_id: int | None = None):
        """Sets from the most recent prior session containing this exercise.

        Powers the "Previous Session Target" badge: returns the full set list
        from the last session (for this exercise's owner) so the UI can show
        exactly what numbers to beat.
        """
        query = (
            db.session.query(WorkoutSession)
            .join(WorkoutSet, WorkoutSet.session_id == WorkoutSession.id)
            .filter(
                WorkoutSession.user_id == self.user_id,
                WorkoutSet.exercise_id == self.id,
            )
        )
        if exclude_session_id is not None:
            query = query.filter(WorkoutSession.id != exclude_session_id)
        last_session = query.order_by(WorkoutSession.started_at.desc()).first()
        if last_session is None:
            return None
        sets = (
            WorkoutSet.query.filter_by(session_id=last_session.id, exercise_id=self.id)
            .order_by(WorkoutSet.set_number)
            .all()
        )
        return {"session": last_session, "sets": sets, "top_set": max(sets, key=lambda s: (s.weight, s.reps))}

    def __repr__(self):
        return f"<Exercise {self.name} (user {self.user_id})>"


class WorkoutSession(db.Model):
    __tablename__ = "workout_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default="Workout")
    workout_type = db.Column(db.String(32), nullable=True)  # push, pull, legs — focus for suggestions
    use_split_template = db.Column(db.Boolean, nullable=False, default=False)  # True = full template plan
    planned_exercise_ids = db.Column(db.Text, nullable=False, default="[]")  # user-picked queue (on-the-fly)
    routine_id = db.Column(db.Integer, db.ForeignKey("workout_routines.id"), nullable=True, index=True)
    skipped_exercise_ids = db.Column(db.Text, nullable=False, default="[]")
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    sets = db.relationship(
        "WorkoutSet", backref="session", lazy="dynamic",
        cascade="all, delete-orphan", order_by="WorkoutSet.set_number",
    )

    @property
    def is_active(self) -> bool:
        return self.finished_at is None

    @property
    def total_sets(self) -> int:
        return self.sets.count()

    @property
    def total_volume(self) -> float:
        """Total tonnage (sum of weight * reps) for completed working sets."""
        return round(
            sum(s.weight * s.reps for s in self.sets if s.completed and not s.is_warmup), 1
        )

    @property
    def duration_minutes(self) -> int | None:
        if self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return max(1, int(delta.total_seconds() // 60))

    @property
    def elapsed_minutes(self) -> int:
        end = self.finished_at or utcnow()
        return max(0, int((end - self.started_at).total_seconds() // 60))

    @property
    def exercises_performed(self):
        seen, ordered = set(), []
        for s in self.sets.order_by(WorkoutSet.id):
            if s.exercise_id not in seen:
                seen.add(s.exercise_id)
                ordered.append(s.exercise)
        return ordered

    def sets_for_exercise(self, exercise_id: int):
        return (
            self.sets.filter_by(exercise_id=exercise_id)
            .order_by(WorkoutSet.set_number)
            .all()
        )

    def skipped_ids(self) -> set[int]:
        try:
            raw = json.loads(self.skipped_exercise_ids or "[]")
            return {int(x) for x in raw}
        except (json.JSONDecodeError, TypeError, ValueError):
            return set()

    def skip_exercise(self, exercise_id: int) -> None:
        ids = self.skipped_ids()
        ids.add(exercise_id)
        self.skipped_exercise_ids = json.dumps(sorted(ids))

    def unskip_exercise(self, exercise_id: int) -> None:
        ids = self.skipped_ids()
        ids.discard(exercise_id)
        self.skipped_exercise_ids = json.dumps(sorted(list(ids)))

    def planned_ids(self) -> list[int]:
        try:
            raw = json.loads(self.planned_exercise_ids or "[]")
            return [int(x) for x in raw]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def planned_exercises(self) -> list["Exercise"]:
        ids = self.planned_ids()
        if not ids:
            return []
        by_id = {
            ex.id: ex
            for ex in Exercise.query.filter(
                Exercise.user_id == self.user_id,
                Exercise.id.in_(ids),
            ).all()
        }
        return [by_id[i] for i in ids if i in by_id]

    def add_planned_exercise(self, exercise_id: int) -> None:
        ids = self.planned_ids()
        if exercise_id not in ids:
            ids.append(exercise_id)
        self.planned_exercise_ids = json.dumps(ids)

    def remove_planned_exercise(self, exercise_id: int) -> None:
        self.planned_exercise_ids = json.dumps([i for i in self.planned_ids() if i != exercise_id])
        self.unskip_exercise(exercise_id)

    def __repr__(self):
        return f"<WorkoutSession {self.id} user={self.user_id}>"


class WorkoutSet(db.Model):
    __tablename__ = "workout_sets"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("workout_sessions.id"), nullable=False, index=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False, index=True)
    set_number = db.Column(db.Integer, nullable=False, default=1)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)  # lb
    rpe = db.Column(db.Float, nullable=True)  # rate of perceived exertion (6–10)
    is_warmup = db.Column(db.Boolean, nullable=False, default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    @property
    def volume(self) -> float:
        if not self.completed or self.is_warmup:
            return 0.0
        return round(self.weight * self.reps, 1)

    @property
    def estimated_1rm(self) -> float:
        """Epley formula — useful for comparing sets at different rep ranges."""
        if self.reps <= 0 or self.is_warmup:
            return 0.0
        return round(self.weight * (1 + self.reps / 30), 1)

    def __repr__(self):
        return f"<WorkoutSet {self.weight}lb x {self.reps}>"


class WeightLog(db.Model):
    __tablename__ = "weight_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    weight = db.Column(db.Float, nullable=False)        # lb — VeSync may need conversion on sync
    body_fat = db.Column(db.Float, nullable=True)       # percent

    __table_args__ = (db.UniqueConstraint("user_id", "log_date", name="uq_weight_user_date"),)

    def __repr__(self):
        return f"<WeightLog {self.log_date} {self.weight}lb>"


class WorkoutRoutine(db.Model):
    __tablename__ = "workout_routines"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    split_key = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    entries = db.relationship(
        "WorkoutRoutineExercise",
        backref="routine",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="WorkoutRoutineExercise.sort_order",
    )
    sessions = db.relationship("WorkoutSession", backref="routine", lazy="dynamic")

    def ordered_exercises(self) -> list["WorkoutRoutineExercise"]:
        return self.entries.order_by(WorkoutRoutineExercise.sort_order).all()

    def __repr__(self):
        return f"<WorkoutRoutine {self.name}>"


class WorkoutRoutineExercise(db.Model):
    __tablename__ = "workout_routine_exercises"

    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("workout_routines.id"), nullable=False, index=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    target_sets = db.Column(db.Integer, nullable=False, default=3)
    target_reps = db.Column(db.String(16), nullable=True)  # e.g. "8" or "8-10"

    exercise = db.relationship("Exercise")

    def __repr__(self):
        return f"<RoutineExercise {self.exercise_id} order={self.sort_order}>"


class UserProgramDay(db.Model):
    """Weekly schedule: assign a split or saved routine to each weekday."""
    __tablename__ = "user_program_days"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday … 6=Sunday
    split_key = db.Column(db.String(32), nullable=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("workout_routines.id"), nullable=True)

    routine = db.relationship("WorkoutRoutine")

    __table_args__ = (
        db.UniqueConstraint("user_id", "day_of_week", name="uq_program_user_day"),
    )

    @property
    def label(self) -> str:
        if self.routine:
            return self.routine.name
        if self.split_key:
            return self.split_key.replace("_", " ").title()
        return "Rest"

    def __repr__(self):
        return f"<UserProgramDay user={self.user_id} dow={self.day_of_week}>"
