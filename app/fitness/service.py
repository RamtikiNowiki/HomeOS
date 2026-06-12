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
    STARTER_EXERCISES,
    catalog_entry,
    get_split,
    get_split_exercise_names,
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
    done = [ex for ex in recommended if ex.id in performed_ids]
    remaining = [ex for ex in recommended if ex.id not in performed_ids]
    return {
        "recommended": recommended,
        "done": done,
        "remaining": remaining,
        "total": len(recommended),
        "done_count": len(done),
    }


def next_exercise_in_session(session, current_exercise_id: int, split_id: str | None) -> Exercise | None:
    """Next exercise to log: routine order, then split, then library."""
    performed_ids = {ex.id for ex in session.exercises_performed}
    performed_ids.add(current_exercise_id)

    if session.routine_id:
        routine = db.session.get(WorkoutRoutine, session.routine_id)
        if routine:
            for entry in routine.ordered_exercises():
                if entry.exercise_id not in performed_ids:
                    return entry.exercise

    if split_id:
        for ex in resolve_split_exercises(session.user_id, split_id):
            if ex.id not in performed_ids:
                return ex

    all_exercises = (
        Exercise.query.filter_by(user_id=session.user_id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    for ex in all_exercises:
        if ex.id not in performed_ids:
            return ex
    return None


def routine_progress(session, routine: WorkoutRoutine) -> dict:
    ordered = [e.exercise for e in routine.ordered_exercises()]
    performed_ids = {ex.id for ex in session.exercises_performed}
    done = [ex for ex in ordered if ex.id in performed_ids]
    remaining = [ex for ex in ordered if ex.id not in performed_ids]
    return {
        "recommended": ordered,
        "entries": routine.ordered_exercises(),
        "done": done,
        "remaining": remaining,
        "total": len(ordered),
        "done_count": len(done),
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

