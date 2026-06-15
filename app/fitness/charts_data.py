"""Aggregate fitness data for charts (server-side JSON for Chart.js)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func

from ..extensions import db
from ..models import Exercise, WeightLog, WorkoutSession, WorkoutSet, utcnow


def weight_chart(user_id: int, limit: int = 30) -> dict:
    logs = (
        WeightLog.query.filter_by(user_id=user_id)
        .order_by(WeightLog.log_date.asc())
        .limit(limit)
        .all()
    )
    return {
        "labels": [l.log_date.strftime("%b %d") for l in logs],
        "values": [l.weight for l in logs],
    }


def weekly_volume_chart(user_id: int, weeks: int = 12) -> dict:
    if db.engine.dialect.name == "sqlite":
        start = utcnow() - timedelta(weeks=weeks)
        rows = (
            db.session.query(
                func.strftime("%Y-W%W", WorkoutSession.started_at).label("week"),
                func.sum(WorkoutSet.weight * WorkoutSet.reps).label("volume"),
            )
            .join(WorkoutSet, WorkoutSet.session_id == WorkoutSession.id)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.finished_at.isnot(None),
                WorkoutSession.started_at >= start,
                WorkoutSet.completed.is_(True),
                WorkoutSet.is_warmup.is_(False),
            )
            .group_by("week")
            .order_by("week")
            .all()
        )
        if not rows:
            rows = _weekly_volume_fallback(user_id, weeks)
    else:
        rows = _weekly_volume_fallback(user_id, weeks)
    return {
        "labels": [r[0] for r in rows],
        "values": [round(float(r[1] or 0), 1) for r in rows],
    }


def _weekly_volume_fallback(user_id: int, weeks: int) -> list:
    """Build weekly buckets in Python when strftime week grouping differs."""
    start = utcnow() - timedelta(weeks=weeks)
    sessions = (
        WorkoutSession.query.filter_by(user_id=user_id)
        .filter(
            WorkoutSession.finished_at.isnot(None),
            WorkoutSession.started_at >= start,
        )
        .all()
    )
    buckets: dict[str, float] = {}
    for s in sessions:
        key = s.started_at.strftime("%Y-W%W")
        buckets[key] = buckets.get(key, 0.0) + s.total_volume
    return sorted(buckets.items())


def exercise_progress_chart(user_id: int, exercise_id: int, limit: int = 20) -> dict:
    rows = (
        db.session.query(
            WorkoutSession.started_at,
            func.max(WorkoutSet.weight * (1 + WorkoutSet.reps / 30.0)).label("est_1rm"),
        )
        .join(WorkoutSet, WorkoutSet.session_id == WorkoutSession.id)
        .filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.finished_at.isnot(None),
            WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.completed.is_(True),
            WorkoutSet.is_warmup.is_(False),
        )
        .group_by(WorkoutSession.id, WorkoutSession.started_at)
        .order_by(WorkoutSession.started_at.asc())
        .limit(limit)
        .all()
    )
    return {
        "labels": [r[0].strftime("%b %d") for r in rows],
        "values": [round(float(r[1] or 0), 1) for r in rows],
    }


def pr_timeline(user_id: int, limit: int = 15) -> list[dict]:
    """Recent personal records across all exercises."""
    exercises = Exercise.query.filter_by(user_id=user_id).all()
    events: list[dict] = []
    for ex in exercises:
        sets = (
            WorkoutSet.query.join(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSet.exercise_id == ex.id,
                WorkoutSet.completed.is_(True),
                WorkoutSet.is_warmup.is_(False),
            )
            .order_by(WorkoutSession.started_at.asc())
            .all()
        )
        best_so_far = 0.0
        for s in sets:
            est = s.estimated_1rm
            if est > best_so_far:
                best_so_far = est
                events.append({
                    "date": s.session.started_at,
                    "exercise": ex.name,
                    "weight": s.weight,
                    "reps": s.reps,
                    "estimated_1rm": est,
                })
    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]
