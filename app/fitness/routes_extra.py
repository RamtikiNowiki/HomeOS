"""Additional fitness routes — routines, charts, program, plates, repeat session."""
from __future__ import annotations

import json

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Exercise, WorkoutRoutine, WorkoutRoutineExercise, WorkoutSession, UserProgramDay
from . import fitness_bp
from .catalog import WORKOUT_SPLITS, get_split
from .charts_data import exercise_progress_chart, pr_timeline, weekly_volume_chart, weight_chart
from .plates import calculate_plates, DEFAULT_BAR
from .routes import _get_own_exercise, _get_own_session
from .service import (
    DAY_NAMES,
    copy_previous_sets_to_session,
    create_routine_from_session,
    find_last_session_to_repeat,
    get_program_week,
    parse_plan_rows_from_form,
    plan_entries_from_routine,
    plan_entries_from_split,
    repeat_session,
    save_routine_plan,
    start_session_from_program_day,
    start_session_from_routine,
)


def _get_own_routine(routine_id: int) -> WorkoutRoutine:
    routine = db.session.get(WorkoutRoutine, routine_id)
    if routine is None or routine.user_id != current_user.id:
        abort(404)
    return routine


# ---------------------------------------------------------------------------
# Repeat last session
# ---------------------------------------------------------------------------

@fitness_bp.route("/session/repeat-last", methods=["POST"])
@login_required
def repeat_last_session():
    workout_type = request.form.get("workout_type", "").strip() or None
    name = request.form.get("name", "").strip() or None
    source = find_last_session_to_repeat(
        current_user.id, name=name, workout_type=workout_type
    )
    if source is None:
        flash("No previous session found to repeat.", "error")
        return redirect(url_for("fitness.index"))
    session = repeat_session(current_user.id, source)
    flash(f"Repeating “{source.name}” — log your sets.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>/repeat", methods=["POST"])
@login_required
def repeat_session_route(session_id: int):
    source = _get_own_session(session_id)
    if not source.finished_at:
        flash("Finish the session before repeating it.", "error")
        return redirect(url_for("fitness.session_detail", session_id=session_id))
    session = repeat_session(current_user.id, source)
    flash("Session repeated — same exercises, beat your last numbers.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>/save-routine", methods=["POST"])
@login_required
def save_session_as_routine(session_id: int):
    session = _get_own_session(session_id)
    name = request.form.get("name", "").strip() or session.name
    if not session.exercises_performed:
        flash("Log at least one exercise before saving a routine.", "error")
        return redirect(url_for("fitness.session_detail", session_id=session_id))
    routine = create_routine_from_session(current_user.id, session, name)
    flash(f"Saved routine “{routine.name}”.", "success")
    return redirect(url_for("fitness.routines"))


@fitness_bp.route(
    "/session/<int:session_id>/exercise/<int:exercise_id>/copy-previous", methods=["POST"]
)
@login_required
def copy_previous_sets(session_id: int, exercise_id: int):
    session = _get_own_session(session_id)
    exercise = _get_own_exercise(exercise_id)
    count = copy_previous_sets_to_session(session, exercise)
    if count:
        flash(f"Copied {count} set(s) from your last session.", "success")
    else:
        flash("Nothing to copy — no prior session or sets already logged.", "error")
    return redirect(
        url_for("fitness.log_exercise", session_id=session.id, exercise_id=exercise.id)
    )


# ---------------------------------------------------------------------------
# Custom routines
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Workout planner — customize templates, plan in advance, preview before start
# ---------------------------------------------------------------------------

@fitness_bp.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
    split_id = request.args.get("split", "").strip() or request.form.get("split_key", "").strip() or None
    routine_id = request.args.get("routine_id", type=int) or request.form.get("routine_id", type=int)
    split = get_split(split_id) if split_id else None

    if request.method == "POST":
        action = request.form.get("action", "save")
        name = request.form.get("name", "").strip()
        split_key = request.form.get("split_key", "").strip() or None
        rid = request.form.get("routine_id", type=int)
        rows = parse_plan_rows_from_form(request.form)

        if not name:
            flash("Give your workout a name.", "error")
            return redirect(request.referrer or url_for("fitness.plan"))
        if not rows:
            flash("Add at least one exercise to the plan.", "error")
            return redirect(request.referrer or url_for("fitness.plan"))

        try:
            routine = save_routine_plan(
                current_user.id,
                name,
                rows,
                split_key=split_key,
                routine_id=rid,
            )
        except ValueError:
            abort(404)

        if action == "start":
            existing = WorkoutSession.query.filter_by(
                user_id=current_user.id, finished_at=None
            ).first()
            if existing:
                flash("Finish or discard your current workout before starting a new one.", "error")
                return redirect(url_for("fitness.session_detail", session_id=existing.id))
            session = start_session_from_routine(current_user.id, routine)
            flash(f"Started “{routine.name}” — log when you're ready.", "success")
            return redirect(url_for("fitness.session_detail", session_id=session.id))

        flash(f"Saved workout plan “{routine.name}”.", "success")
        return redirect(url_for("fitness.routine_detail", routine_id=routine.id))

    # GET — load plan editor
    entries = []
    name = ""
    editing_routine = None
    if routine_id:
        editing_routine = _get_own_routine(routine_id)
        name = editing_routine.name
        split_id = editing_routine.split_key
        split = get_split(split_id) if split_id else None
        entries = plan_entries_from_routine(editing_routine)
    elif split_id and split:
        name = split["name"]
        entries = plan_entries_from_split(current_user.id, split_id)
    else:
        name = request.args.get("name", "").strip()

    exercises = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    return render_template(
        "fitness/plan.html",
        name=name,
        entries=entries,
        exercises=exercises,
        split_id=split_id,
        split=split,
        routine=editing_routine,
        splits=WORKOUT_SPLITS,
    )


@fitness_bp.route("/routines/<int:routine_id>")
@login_required
def routine_detail(routine_id: int):
    """Preview a saved workout plan before starting."""
    routine = _get_own_routine(routine_id)
    entries = routine.ordered_exercises()
    return render_template(
        "fitness/routine_detail.html",
        routine=routine,
        entries=entries,
    )


@fitness_bp.route("/routines")
@login_required
def routines():
    items = (
        WorkoutRoutine.query.filter_by(user_id=current_user.id)
        .order_by(WorkoutRoutine.name)
        .all()
    )
    last_by_type = {}
    for split_id in WORKOUT_SPLITS:
        last = find_last_session_to_repeat(current_user.id, workout_type=split_id)
        if last:
            last_by_type[split_id] = last
    return render_template(
        "fitness/routines.html",
        routines=items,
        splits=WORKOUT_SPLITS,
        last_by_type=last_by_type,
    )


@fitness_bp.route("/routines/new", methods=["GET", "POST"])
@login_required
def routine_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        split_key = request.form.get("split_key", "").strip() or None
        if not name:
            flash("Routine name is required.", "error")
            return redirect(url_for("fitness.routine_new"))
        params = {"routine_id": None}
        if split_key:
            return redirect(url_for("fitness.plan", split=split_key, name=name))
        routine = WorkoutRoutine(
            user_id=current_user.id, name=name, split_key=split_key
        )
        db.session.add(routine)
        db.session.commit()
        return redirect(url_for("fitness.plan", routine_id=routine.id))

    return redirect(url_for("fitness.plan"))


@fitness_bp.route("/routines/<int:routine_id>/edit", methods=["GET", "POST"])
@login_required
def routine_edit(routine_id: int):
    """Legacy URL — planner is the editor now."""
    _get_own_routine(routine_id)
    return redirect(url_for("fitness.plan", routine_id=routine_id))


@fitness_bp.route("/routines/quick", methods=["POST"])
@login_required
def routine_quick_create():
    """Redirect inline quick-create to the full planner."""
    return redirect(url_for("fitness.plan"))


@fitness_bp.route("/routines/<int:routine_id>/delete", methods=["POST"])
@login_required
def routine_delete(routine_id: int):
    routine = _get_own_routine(routine_id)
    name = routine.name
    db.session.delete(routine)
    db.session.commit()
    flash(f"Deleted routine “{name}”.", "success")
    return redirect(url_for("fitness.routines"))


@fitness_bp.route("/routines/<int:routine_id>/start", methods=["POST"])
@login_required
def routine_start(routine_id: int):
    routine = _get_own_routine(routine_id)
    session = start_session_from_routine(current_user.id, routine)
    flash(f"Started “{routine.name}”.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


# ---------------------------------------------------------------------------
# Weekly program
# ---------------------------------------------------------------------------

@fitness_bp.route("/program", methods=["GET", "POST"])
@login_required
def program():
    if request.method == "POST":
        UserProgramDay.query.filter_by(user_id=current_user.id).delete()
        for dow in range(7):
            choice = request.form.get(f"day_{dow}", "").strip()
            if not choice or choice == "rest":
                continue
            if choice.startswith("split:"):
                db.session.add(
                    UserProgramDay(
                        user_id=current_user.id,
                        day_of_week=dow,
                        split_key=choice.split(":", 1)[1],
                    )
                )
            elif choice.startswith("routine:"):
                rid = int(choice.split(":", 1)[1])
                routine = _get_own_routine(rid)
                db.session.add(
                    UserProgramDay(
                        user_id=current_user.id,
                        day_of_week=dow,
                        routine_id=routine.id,
                    )
                )
        db.session.commit()
        flash("Weekly program saved.", "success")
        return redirect(url_for("fitness.program"))

    from datetime import datetime
    today_dow = datetime.now().weekday()  # 0=Monday
    week = get_program_week(current_user.id)
    routines_list = (
        WorkoutRoutine.query.filter_by(user_id=current_user.id)
        .order_by(WorkoutRoutine.name)
        .all()
    )
    return render_template(
        "fitness/program.html",
        day_names=DAY_NAMES,
        week=week,
        today_dow=today_dow,
        splits=WORKOUT_SPLITS,
        routines=routines_list,
    )


@fitness_bp.route("/program/start-today", methods=["POST"])
@login_required
def program_start_today():
    from datetime import datetime
    dow = datetime.now().weekday()
    day = UserProgramDay.query.filter_by(
        user_id=current_user.id, day_of_week=dow
    ).first()
    if day is None:
        flash("No workout scheduled for today — set up your program first.", "error")
        return redirect(url_for("fitness.program"))
    session = start_session_from_program_day(current_user.id, day)
    if session is None:
        flash("Today is a rest day.", "success")
        return redirect(url_for("fitness.program"))
    flash(f"Started {day.label}.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

@fitness_bp.route("/charts")
@login_required
def charts():
    exercises = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    selected_id = request.args.get("exercise", type=int)
    if selected_id:
        ex = db.session.get(Exercise, selected_id)
        if ex is None or ex.user_id != current_user.id:
            selected_id = exercises[0].id if exercises else None
    elif exercises:
        selected_id = exercises[0].id

    exercise_chart = (
        exercise_progress_chart(current_user.id, selected_id) if selected_id else {"labels": [], "values": []}
    )
    return render_template(
        "fitness/charts.html",
        weight_data=json.dumps(weight_chart(current_user.id)),
        volume_data=json.dumps(weekly_volume_chart(current_user.id)),
        exercise_data=json.dumps(exercise_chart),
        pr_events=pr_timeline(current_user.id),
        exercises=exercises,
        selected_exercise_id=selected_id,
    )


# ---------------------------------------------------------------------------
# Plate calculator
# ---------------------------------------------------------------------------

@fitness_bp.route("/plates", methods=["GET", "POST"])
@login_required
def plates():
    result = None
    target = bar = DEFAULT_BAR
    if request.method == "POST":
        try:
            target = float(request.form.get("target", 0))
            bar = float(request.form.get("bar", DEFAULT_BAR))
        except ValueError:
            flash("Enter valid numbers.", "error")
        else:
            result = calculate_plates(target, bar)
    return render_template("fitness/plates.html", result=result, target=target, bar=bar)
