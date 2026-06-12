from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..home_assistant.service import HomeAssistantService
from ..creality_k2.service import CrealityK2Service
from ..models import WeightLog, WorkoutSession
from ..fitness.service import (
    last_logged_exercise,
    suggest_next_exercise,
    get_program_week,
    workout_streak_stats,
)
from datetime import datetime
from . import main_bp

DEFAULT_PREFERENCES = {
    "default_rest_seconds": 90,
    "rest_sound": False,
    "pr_sound": False,
    "seasonal_bg": True,
}


def _weight_trend(user_id: int, limit: int = 12):
    """Latest weight, delta vs previous log, and SVG sparkline points."""
    logs = (
        WeightLog.query.filter_by(user_id=user_id)
        .order_by(WeightLog.log_date.desc())
        .limit(limit)
        .all()
    )
    logs.reverse()
    if not logs:
        return {"latest": None, "delta": None, "points": "", "logs": []}

    latest = logs[-1]
    delta = round(logs[-1].weight - logs[-2].weight, 1) if len(logs) > 1 else None

    # Normalize into a 100x32 viewBox polyline
    points = ""
    if len(logs) > 1:
        weights = [l.weight for l in logs]
        lo, hi = min(weights), max(weights)
        span = (hi - lo) or 1.0
        step = 100 / (len(weights) - 1)
        coords = [
            f"{round(i * step, 1)},{round(30 - ((w - lo) / span) * 28, 1)}"
            for i, w in enumerate(weights)
        ]
        points = " ".join(coords)

    return {"latest": latest, "delta": delta, "points": points, "logs": logs}


@main_bp.route("/")
@login_required
def dashboard():
    last_session = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .first()
    )
    active_session = (
        WorkoutSession.query.filter_by(user_id=current_user.id, finished_at=None)
        .order_by(WorkoutSession.started_at.desc())
        .first()
    )
    next_exercise = None
    last_exercise = None
    if active_session:
        last_exercise = last_logged_exercise(active_session)
        next_exercise = suggest_next_exercise(active_session)

    ha = HomeAssistantService()
    lights = ha.get_lights()
    sensor = ha.get_sensor()
    lights_on = sum(1 for l in lights if l["state"] == "on")

    printer = CrealityK2Service().get_status()

    week = get_program_week(current_user.id)
    today_program = week[datetime.now().weekday()]
    streak = workout_streak_stats(current_user.id)

    return render_template(
        "dashboard.html",
        weight=_weight_trend(current_user.id),
        last_session=last_session,
        active_session=active_session,
        next_exercise=next_exercise,
        last_exercise=last_exercise,
        today_program=today_program,
        streak=streak,
        lights=lights,
        lights_on=lights_on,
        sensor=sensor,
        printer=printer,
    )


def _merged_preferences(user) -> dict:
    prefs = dict(DEFAULT_PREFERENCES)
    prefs.update(user.get_preferences())
    return prefs


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    ha = HomeAssistantService()
    printer = CrealityK2Service()

    if request.method == "POST":
        rest_raw = request.form.get("default_rest_seconds", "90")
        try:
            rest_sec = max(30, min(600, int(rest_raw)))
        except ValueError:
            rest_sec = 90
        current_user.set_preferences({
            "default_rest_seconds": rest_sec,
            "rest_sound": request.form.get("rest_sound") == "1",
            "pr_sound": request.form.get("pr_sound") == "1",
            "seasonal_bg": request.form.get("seasonal_bg") == "1",
        })
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))

    return render_template(
        "settings.html",
        prefs=_merged_preferences(current_user),
        ha_info=ha.connection_info(),
        printer_info=printer.connection_info(),
        is_ha_mock=ha.is_mock,
        is_printer_mock=printer.is_mock,
    )
