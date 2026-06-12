"""Fitness business logic — exercise import, split helpers."""
from __future__ import annotations

from ..extensions import db
from ..models import (
    Exercise,
    UserProgramDay,
    WorkoutRoutine,
    WorkoutRoutineExercise,
    WorkoutSession,
    WorkoutSet,
    utcnow,
)
from .catalog import (
    BEGINNER_EXERCISES,
    STARTER_EXERCISES,
    catalog_entry,
    get_split,
    get_split_exercise_names,
    infer_split_key_from_name,
    muscle_groups_for_split,
)


def user_exercise_names(user_id: int) -> set[str]:
    return {
        name
        for (name,) in db.session.query(Exercise.name).filter_by(user_id=user_id).all()
    }


def import_catalog_exercises(user_id: int, names: list[str]) -> tuple[int, int]:
    """Add catalog exercises to a user's library. Returns (added, skipped)."""
    existing = user_exercise_names(user_id)
    added = skipped = 0
    for name in names:
        if name in existing:
            skipped += 1
            continue
        entry = catalog_entry(name)
        if entry is None:
            skipped += 1
            continue
        db.session.add(
            Exercise(user_id=user_id, name=entry.name, muscle_group=entry.muscle_group)
        )
        existing.add(name)
        added += 1
    if added:
        db.session.commit()
    return added, skipped


def import_starter_library(user_id: int) -> tuple[int, int]:
    return import_catalog_exercises(user_id, list(STARTER_EXERCISES))


def import_beginner_library(user_id: int) -> tuple[int, int]:
    return import_catalog_exercises(user_id, list(BEGINNER_EXERCISES))


def check_set_beats_pr(exercise: Exercise, weight: float, reps: int, is_warmup: bool) -> dict | None:
    """Return PR info if this working set beats the previous best est. 1RM."""
    if is_warmup or reps < 1 or weight <= 0:
        return None
    new_1rm = weight * (1 + reps / 30.0)
    prev = exercise.personal_record()
    if prev is None or new_1rm > prev["estimated_1rm"] + 0.01:
        return {
            "weight": weight,
            "reps": reps,
            "estimated_1rm": round(new_1rm, 1),
            "previous_1rm": round(prev["estimated_1rm"], 1) if prev else None,
        }
    return None


def workout_streak_stats(user_id: int) -> dict:
    """Weekly session count and consecutive-day workout streak."""
    from datetime import timedelta

    finished = (
        WorkoutSession.query.filter_by(user_id=user_id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .all()
    )
    if not finished:
        return {"weekly_sessions": 0, "day_streak": 0}

    now = utcnow()
    week_ago = now - timedelta(days=7)
    weekly = sum(1 for s in finished if s.started_at >= week_ago)

    days_with_workouts = sorted(
        {s.started_at.date() for s in finished},
        reverse=True,
    )
    streak = 0
    if days_with_workouts:
        cursor = now.date()
        if cursor not in days_with_workouts:
            cursor -= timedelta(days=1)
        for d in days_with_workouts:
            if d == cursor:
                streak += 1
                cursor -= timedelta(days=1)
            elif d < cursor:
                break

    return {"weekly_sessions": weekly, "day_streak": streak}


def import_split_exercises(user_id: int, split_id: str) -> tuple[int, int]:
    names = get_split_exercise_names(split_id)
    if not names:
        return 0, 0
    return import_catalog_exercises(user_id, names)


def resolve_split_exercises(user_id: int, split_id: str) -> list[Exercise]:
    """Exercises from the user's library that match a split template, in template order."""
    names = get_split_exercise_names(split_id)
    if not names:
        return []
    by_name = {
        ex.name: ex
        for ex in Exercise.query.filter(
            Exercise.user_id == user_id,
            Exercise.name.in_(names),
        ).all()
    }
    return [by_name[n] for n in names if n in by_name]


def split_progress(session, split_id: str) -> dict:
    """How far through a split template the current session is."""
    recommended = resolve_split_exercises(session.user_id, split_id)
    performed_ids = {ex.id for ex in session.exercises_performed}
    skipped_ids = session.skipped_ids()
    done = [ex for ex in recommended if ex.id in performed_ids]
    skipped = [ex for ex in recommended if ex.id in skipped_ids and ex.id not in performed_ids]
    remaining = [
        ex for ex in recommended
        if ex.id not in performed_ids and ex.id not in skipped_ids
    ]
    return {
        "recommended": recommended,
        "done": done,
        "skipped": skipped,
        "remaining": remaining,
        "total": len(recommended),
        "done_count": len(done),
        "skipped_count": len(skipped),
    }


def next_exercise_in_session(session, current_exercise_id: int, split_id: str | None) -> Exercise | None:
    """Next exercise to log: routine order, then split, then library."""
    performed_ids = {ex.id for ex in session.exercises_performed}
    skipped_ids = session.skipped_ids()
    performed_ids.add(current_exercise_id)

    if session.planned_ids():
        for ex in session.planned_exercises():
            if ex.id not in performed_ids and ex.id not in skipped_ids:
                return ex

    if session.routine_id:
        routine = db.session.get(WorkoutRoutine, session.routine_id)
        if routine:
            for entry in routine.ordered_exercises():
                if entry.exercise_id not in performed_ids and entry.exercise_id not in skipped_ids:
                    return entry.exercise

    effective_split = split_id or (session.workout_type if session.use_split_template else None)
    if effective_split:
        for ex in resolve_split_exercises(session.user_id, effective_split):
            if ex.id not in performed_ids and ex.id not in skipped_ids:
                return ex

    all_exercises = sort_exercises_for_session(
        session,
        Exercise.query.filter_by(user_id=session.user_id).all(),
    )
    for ex in all_exercises:
        if ex.id not in performed_ids and ex.id not in skipped_ids:
            return ex
    return None


def routine_progress(session, routine: WorkoutRoutine) -> dict:
    ordered = [e.exercise for e in routine.ordered_exercises()]
    performed_ids = {ex.id for ex in session.exercises_performed}
    skipped_ids = session.skipped_ids()
    done = [ex for ex in ordered if ex.id in performed_ids]
    skipped = [ex for ex in ordered if ex.id in skipped_ids and ex.id not in performed_ids]
    remaining = [
        ex for ex in ordered
        if ex.id not in performed_ids and ex.id not in skipped_ids
    ]
    return {
        "recommended": ordered,
        "entries": routine.ordered_exercises(),
        "done": done,
        "skipped": skipped,
        "remaining": remaining,
        "total": len(ordered),
        "done_count": len(done),
        "skipped_count": len(skipped),
    }


def start_session_from_routine(user_id: int, routine: WorkoutRoutine) -> WorkoutSession:
    existing = WorkoutSession.query.filter_by(user_id=user_id, finished_at=None).first()
    if existing:
        return existing
    if routine.split_key:
        import_split_exercises(user_id, routine.split_key)
    session = WorkoutSession(
        user_id=user_id,
        name=routine.name,
        workout_type=routine.split_key,
        routine_id=routine.id,
    )
    db.session.add(session)
    db.session.commit()
    return session


def start_session_from_program_day(user_id: int, day: UserProgramDay) -> WorkoutSession | None:
    if day.routine_id:
        routine = db.session.get(WorkoutRoutine, day.routine_id)
        if routine and routine.user_id == user_id:
            return start_session_from_routine(user_id, routine)
    if day.split_key:
        existing = WorkoutSession.query.filter_by(user_id=user_id, finished_at=None).first()
        if existing:
            return existing
        split = get_split(day.split_key)
        if not split:
            return None
        import_split_exercises(user_id, day.split_key)
        session = WorkoutSession(
            user_id=user_id,
            name=split["name"],
            workout_type=day.split_key,
            use_split_template=True,
        )
        db.session.add(session)
        db.session.commit()
        return session
    return None


def repeat_session(user_id: int, source: WorkoutSession) -> WorkoutSession:
    """Start a new session mirroring a finished session's exercise order (no sets copied)."""
    existing = WorkoutSession.query.filter_by(user_id=user_id, finished_at=None).first()
    if existing:
        db.session.delete(existing)
        db.session.flush()

    session = WorkoutSession(
        user_id=user_id,
        name=f"{source.name} (repeat)",
        workout_type=source.workout_type,
        use_split_template=source.use_split_template,
        planned_exercise_ids=source.planned_exercise_ids,
        routine_id=source.routine_id,
    )
    db.session.add(session)
    db.session.commit()
    return session


def find_last_session_to_repeat(user_id: int, name: str | None = None, workout_type: str | None = None):
    q = WorkoutSession.query.filter_by(user_id=user_id).filter(
        WorkoutSession.finished_at.isnot(None)
    )
    if name:
        q = q.filter(WorkoutSession.name == name)
    elif workout_type:
        q = q.filter(WorkoutSession.workout_type == workout_type)
    return q.order_by(WorkoutSession.started_at.desc()).first()


def create_routine_from_session(user_id: int, session: WorkoutSession, name: str) -> WorkoutRoutine:
    routine = WorkoutRoutine(
        user_id=user_id,
        name=name,
        split_key=session.workout_type,
    )
    db.session.add(routine)
    db.session.flush()
    for i, ex in enumerate(session.exercises_performed, start=1):
        sets = session.sets_for_exercise(ex.id)
        working = [s for s in sets if not s.is_warmup]
        target_reps = str(working[0].reps) if working else None
        db.session.add(
            WorkoutRoutineExercise(
                routine_id=routine.id,
                exercise_id=ex.id,
                sort_order=i,
                target_sets=len(working) or 3,
                target_reps=target_reps,
            )
        )
    db.session.commit()
    return routine


def copy_previous_sets_to_session(session: WorkoutSession, exercise: Exercise) -> int:
    """Copy all sets from the last session for this exercise into the current session."""
    previous = exercise.last_completed_session_sets(exclude_session_id=session.id)
    if not previous or not previous["sets"]:
        return 0
    existing = session.sets_for_exercise(exercise.id)
    if existing:
        return 0
    added = 0
    for i, s in enumerate(previous["sets"], start=1):
        db.session.add(
            WorkoutSet(
                session_id=session.id,
                exercise_id=exercise.id,
                set_number=i,
                weight=s.weight,
                reps=s.reps,
                rpe=s.rpe,
                is_warmup=s.is_warmup,
                completed=False,
            )
        )
        added += 1
    db.session.commit()
    return added


def get_program_week(user_id: int) -> list[UserProgramDay | None]:
    days = {
        d.day_of_week: d
        for d in UserProgramDay.query.filter_by(user_id=user_id).all()
    }
    return [days.get(i) for i in range(7)]


DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def resolved_split_key(session: WorkoutSession) -> str | None:
    """Split template for this session — explicit type or inferred from the name."""
    if session.workout_type:
        return session.workout_type
    return infer_split_key_from_name(session.name or "")


def default_muscle_filter_for_session(session: WorkoutSession) -> str:
    """Pre-select a muscle chip when the session has a focus but no fixed template."""
    if not session.workout_type or session.use_split_template or session.routine_id:
        return ""
    primary = {
        "legs": "Legs",
        "lower": "Legs",
        "chest": "Chest",
        "back": "Back",
        "shoulders": "Shoulders",
        "arms": "Arms",
        "push": "Chest",
        "pull": "Back",
    }
    return primary.get(session.workout_type, "")


def sort_exercises_for_session(session: WorkoutSession, exercises: list[Exercise]) -> list[Exercise]:
    """Put session-relevant exercises first (split order, then muscle group)."""
    split_key = resolved_split_key(session)
    if not split_key:
        return exercises

    split_order = {
        ex.id: i
        for i, ex in enumerate(resolve_split_exercises(session.user_id, split_key))
    }
    focus_groups = muscle_groups_for_split(split_key)

    def sort_key(ex: Exercise) -> tuple:
        in_split = 0 if ex.id in split_order else 1
        group_rank = 0 if ex.muscle_group in focus_groups else 1
        split_rank = split_order.get(ex.id, 999)
        return (in_split, group_rank, split_rank, ex.muscle_group, ex.name.lower())

    return sorted(exercises, key=sort_key)


def custom_plan_progress(session: WorkoutSession) -> dict:
    """Progress through a user-built on-the-fly exercise queue."""
    recommended = session.planned_exercises()
    performed_ids = {ex.id for ex in session.exercises_performed}
    skipped_ids = session.skipped_ids()
    done = [ex for ex in recommended if ex.id in performed_ids]
    skipped = [ex for ex in recommended if ex.id in skipped_ids and ex.id not in performed_ids]
    remaining = [
        ex for ex in recommended
        if ex.id not in performed_ids and ex.id not in skipped_ids
    ]
    return {
        "recommended": recommended,
        "done": done,
        "skipped": skipped,
        "remaining": remaining,
        "total": len(recommended),
        "done_count": len(done),
        "skipped_count": len(skipped),
        "ad_hoc": True,
    }


def session_plan_progress(session: WorkoutSession) -> dict | None:
    """Split, routine, or user-picked plan progress for an active session."""
    if session.routine_id and session.routine:
        progress = routine_progress(session, session.routine)
        progress["ad_hoc"] = False
        return progress
    if session.planned_ids():
        return custom_plan_progress(session)
    if session.use_split_template and session.workout_type:
        import_split_exercises(session.user_id, session.workout_type)
        progress = split_progress(session, session.workout_type)
        progress["ad_hoc"] = False
        return progress
    return None


def last_logged_exercise(session: WorkoutSession) -> Exercise | None:
    """Most recently logged exercise in this session."""
    last_set = session.sets.order_by(WorkoutSet.id.desc()).first()
    return last_set.exercise if last_set else None


def suggest_next_exercise(session: WorkoutSession) -> Exercise | None:
    """Best next exercise to log in this session."""
    progress = session_plan_progress(session)
    if progress and progress.get("remaining"):
        return progress["remaining"][0]
    last = last_logged_exercise(session)
    if last:
        return next_exercise_in_session(session, last.id, session.workout_type)
    if progress and progress.get("recommended"):
        return progress["recommended"][0]
    return None


def plan_entries_from_split(user_id: int, split_id: str) -> list[dict]:
    """Load split template exercises into plan rows (imports missing catalog entries)."""
    import_split_exercises(user_id, split_id)
    exercises = resolve_split_exercises(user_id, split_id)
    return [
        {
            "exercise_id": ex.id,
            "exercise": ex,
            "target_sets": 3,
            "target_reps": "",
        }
        for ex in exercises
    ]


def plan_entries_from_routine(routine: WorkoutRoutine) -> list[dict]:
    return [
        {
            "exercise_id": entry.exercise_id,
            "exercise": entry.exercise,
            "target_sets": entry.target_sets,
            "target_reps": entry.target_reps or "",
        }
        for entry in routine.ordered_exercises()
    ]


def save_routine_plan(
    user_id: int,
    name: str,
    rows: list[dict],
    *,
    split_key: str | None = None,
    routine_id: int | None = None,
) -> WorkoutRoutine:
    """Create or update a saved workout plan (no session, no logging required)."""
    if routine_id:
        routine = db.session.get(WorkoutRoutine, routine_id)
        if routine is None or routine.user_id != user_id:
            raise ValueError("Routine not found")
    else:
        routine = WorkoutRoutine(user_id=user_id, name=name, split_key=split_key)
        db.session.add(routine)
        db.session.flush()

    routine.name = name
    routine.split_key = split_key
    db.session.query(WorkoutRoutineExercise).filter_by(routine_id=routine.id).delete()

    for i, row in enumerate(rows, start=1):
        ex_id = row["exercise_id"]
        ex = db.session.get(Exercise, ex_id)
        if ex is None or ex.user_id != user_id:
            continue
        db.session.add(
            WorkoutRoutineExercise(
                routine_id=routine.id,
                exercise_id=ex.id,
                sort_order=i,
                target_sets=int(row.get("target_sets") or 3),
                target_reps=(row.get("target_reps") or "").strip() or None,
            )
        )

    db.session.commit()
    return routine


def parse_plan_rows_from_form(form) -> list[dict]:
    """Parse exercise_id list + per-row sets/reps from the plan form."""
    rows = []
    seen = set()
    for eid_raw in form.getlist("exercise_id"):
        if not eid_raw or not str(eid_raw).isdigit():
            continue
        eid = int(eid_raw)
        if eid in seen:
            continue
        seen.add(eid)
        sets_raw = form.get(f"target_sets_{eid}", "3")
        reps = form.get(f"target_reps_{eid}", "").strip()
        rows.append({
            "exercise_id": eid,
            "target_sets": int(sets_raw) if str(sets_raw).isdigit() else 3,
            "target_reps": reps,
        })
    return rows

