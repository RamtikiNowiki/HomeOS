"""Fitness navigation helpers — tab state and smart resume URLs."""
from __future__ import annotations

from flask import url_for

from ..models import WorkoutSession
from .service import last_logged_exercise, suggest_next_exercise

HISTORY_TAB = "history"
STATS_TAB = "stats"
TOOLS_TAB = "tools"
TRAIN_TAB = "train"

_TOOLS_ENDPOINTS = frozenset({
    "tools",
    "routines",
    "routine_new",
    "routine_edit",
    "program",
    "catalog",
    "exercises",
    "weight",
    "charts",
    "plates",
})


def fitness_tab_for_endpoint(endpoint: str | None) -> str | None:
    if not endpoint or not endpoint.startswith("fitness."):
        return None
    name = endpoint.split(".", 1)[1]
    if name == "history":
        return HISTORY_TAB
    if name == "stats":
        return STATS_TAB
    if name in _TOOLS_ENDPOINTS:
        return TOOLS_TAB
    return TRAIN_TAB


def workout_entry_url(session: WorkoutSession | None) -> str:
    """Best URL for the Workout tab / Train nav — resume logging when mid-session."""
    if session is None:
        return url_for("fitness.index")
    nxt = suggest_next_exercise(session)
    if nxt:
        return url_for(
            "fitness.log_exercise",
            session_id=session.id,
            exercise_id=nxt.id,
        )
    last = last_logged_exercise(session)
    if last:
        return url_for(
            "fitness.log_exercise",
            session_id=session.id,
            exercise_id=last.id,
        )
    return url_for("fitness.session_detail", session_id=session.id)
