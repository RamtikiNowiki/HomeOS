from datetime import datetime, date, timedelta

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Exercise, WeightLog, WorkoutSession, WorkoutSet, WorkoutRoutine, WorkoutRoutineExercise, UserProgramDay, utcnow
from . import fitness_bp
from .catalog import (
    EXERCISE_CATALOG,
    MUSCLE_GROUPS,
    STARTER_EXERCISES,
    WORKOUT_SPLITS,
    catalog_entry,
    catalog_for_muscle_group,
    get_split,
)
from .service import (
    import_catalog_exercises,
    import_split_exercises,
    import_starter_library,
    next_exercise_in_session,
    resolve_split_exercises,
    routine_progress,
    split_progress,
    user_exercise_names,
)


# ---------------------------------------------------------------------------
# Ownership guards — every query is scoped to current_user.id
# ---------------------------------------------------------------------------

def _get_own_session(session_id: int) -> WorkoutSession:
    session = db.session.get(WorkoutSession, session_id)
    if session is None or session.user_id != current_user.id:
        abort(404)
    return session


def _get_own_exercise(exercise_id: int) -> Exercise:
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None or exercise.user_id != current_user.id:
        abort(404)
    return exercise


def _get_own_set(set_id: int) -> WorkoutSet:
    workout_set = db.session.get(WorkoutSet, set_id)
    if workout_set is None or workout_set.session.user_id != current_user.id:
        abort(404)
    return workout_set


def _parse_set_form() -> tuple[float, int, float | None, bool]:
    weight = float(request.form["weight"])
    reps = int(request.form["reps"])
    rpe_raw = request.form.get("rpe", "").strip()
    rpe = float(rpe_raw) if rpe_raw else None
    is_warmup = request.form.get("is_warmup") == "1"
    if weight < 0 or reps <= 0:
        raise ValueError
    if rpe is not None and not (6 <= rpe <= 10):
        raise ValueError
    return weight, reps, rpe, is_warmup


def _ensure_active_session() -> WorkoutSession:
    """Return the user's active session, creating one if needed."""
    existing = WorkoutSession.query.filter_by(
        user_id=current_user.id, finished_at=None
    ).first()
    if existing:
        return existing
    session = WorkoutSession(
        user_id=current_user.id,
        name=datetime.now().strftime("%A Session"),
    )
    db.session.add(session)
    db.session.commit()
    return session


# ---------------------------------------------------------------------------
# Workout hub
# ---------------------------------------------------------------------------

@fitness_bp.route("/")
@login_required
def index():
    active_session = (
        WorkoutSession.query.filter_by(user_id=current_user.id, finished_at=None)
        .order_by(WorkoutSession.started_at.desc())
        .first()
    )
    exercises = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    recent_sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .limit(5)
        .all()
    )
    latest_weight = (
        WeightLog.query.filter_by(user_id=current_user.id)
        .order_by(WeightLog.log_date.desc())
        .first()
    )
    return render_template(
        "fitness/index.html",
        active_session=active_session,
        exercises=exercises,
        recent_sessions=recent_sessions,
        latest_weight=latest_weight,
        splits=WORKOUT_SPLITS,
        muscle_groups=MUSCLE_GROUPS,
        starter_count=len(STARTER_EXERCISES),
    )


@fitness_bp.route("/session/start", methods=["POST"])
@login_required
def start_session():
    existing = WorkoutSession.query.filter_by(
        user_id=current_user.id, finished_at=None
    ).first()
    if existing:
        return redirect(url_for("fitness.session_detail", session_id=existing.id))

    split_id = request.form.get("split", "").strip() or None
    split = get_split(split_id) if split_id else None

    name = request.form.get("name", "").strip()
    if not name:
        name = split["name"] if split else datetime.now().strftime("%A Session")

    if split_id:
        added, _ = import_split_exercises(current_user.id, split_id)
        if added:
            flash(f"Added {added} exercises to your library.", "success")

    session = WorkoutSession(
        user_id=current_user.id,
        name=name,
        workout_type=split_id,
    )
    db.session.add(session)
    db.session.commit()
    flash("Session started — follow the suggested exercises below.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>")
@login_required
def session_detail(session_id: int):
    session = _get_own_session(session_id)
    exercises = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    performed = [
        {"exercise": ex, "sets": session.sets_for_exercise(ex.id)}
        for ex in session.exercises_performed
    ]
    progress = None
    split_info = None
    if session.routine_id and session.routine:
        progress = routine_progress(session, session.routine)
    elif session.workout_type:
        progress = split_progress(session, session.workout_type)
        split_info = get_split(session.workout_type)
    recommended_ids = {ex.id for ex in progress["recommended"]} if progress else set()
    other_exercises = [ex for ex in exercises if ex.id not in recommended_ids]
    return render_template(
        "fitness/session.html",
        session=session,
        exercises=exercises,
        performed=performed,
        progress=progress,
        split_info=split_info,
        other_exercises=other_exercises,
    )


@fitness_bp.route("/session/<int:session_id>/finish", methods=["POST"])
@login_required
def finish_session(session_id: int):
    session = _get_own_session(session_id)
    if session.total_sets == 0:
        db.session.delete(session)
        db.session.commit()
        flash("Empty session discarded.", "success")
        return redirect(url_for("fitness.index"))
    session.finished_at = utcnow()
    db.session.commit()
    mins = session.duration_minutes
    flash(
        f"Session logged: {session.total_sets} sets, {session.total_volume:g} kg volume"
        + (f", {mins} min." if mins else "."),
        "success",
    )
    return redirect(url_for("fitness.index"))


@fitness_bp.route("/session/<int:session_id>/notes", methods=["POST"])
@login_required
def update_session_notes(session_id: int):
    session = _get_own_session(session_id)
    notes = request.form.get("notes", "").strip() or None
    session.notes = notes
    db.session.commit()
    flash("Session notes saved.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_session(session_id: int):
    session = _get_own_session(session_id)
    db.session.delete(session)
    db.session.commit()
    flash("Session deleted.", "success")
    return redirect(url_for("fitness.history"))


# ---------------------------------------------------------------------------
# Exercise logging — with "Previous Session Target" intelligence
# ---------------------------------------------------------------------------

@fitness_bp.route("/session/<int:session_id>/exercise/<int:exercise_id>")
@login_required
def log_exercise(session_id: int, exercise_id: int):
    session = _get_own_session(session_id)
    exercise = _get_own_exercise(exercise_id)

    current_sets = session.sets_for_exercise(exercise.id)
    previous = exercise.last_completed_session_sets(exclude_session_id=session.id)

    if current_sets:
        last = current_sets[-1]
        prefill = {"weight": last.weight, "reps": last.reps, "rpe": last.rpe or ""}
    elif previous:
        top = previous["top_set"]
        prefill = {"weight": top.weight, "reps": top.reps, "rpe": top.rpe or ""}
    else:
        prefill = {"weight": "", "reps": "", "rpe": ""}

    nxt = next_exercise_in_session(session, exercise.id, session.workout_type)

    return render_template(
        "fitness/log_exercise.html",
        session=session,
        exercise=exercise,
        current_sets=current_sets,
        previous=previous,
        prefill=prefill,
        next_exercise=nxt,
    )


@fitness_bp.route("/exercise/<int:exercise_id>/quick-start", methods=["POST"])
@login_required
def quick_start_exercise(exercise_id: int):
    """Start (or resume) a session and jump straight to logging an exercise."""
    exercise = _get_own_exercise(exercise_id)
    session = _ensure_active_session()
    return redirect(
        url_for("fitness.log_exercise", session_id=session.id, exercise_id=exercise.id)
    )


@fitness_bp.route(
    "/session/<int:session_id>/exercise/<int:exercise_id>/sets", methods=["POST"]
)
@login_required
def add_set(session_id: int, exercise_id: int):
    session = _get_own_session(session_id)
    exercise = _get_own_exercise(exercise_id)

    try:
        weight, reps, rpe, is_warmup = _parse_set_form()
    except (KeyError, ValueError):
        flash("Enter valid weight, reps, and optional RPE (6–10).", "error")
        return redirect(
            url_for("fitness.log_exercise", session_id=session.id, exercise_id=exercise.id)
        )

    next_number = len(session.sets_for_exercise(exercise.id)) + 1
    db.session.add(
        WorkoutSet(
            session_id=session.id,
            exercise_id=exercise.id,
            set_number=next_number,
            reps=reps,
            weight=weight,
            rpe=rpe,
            is_warmup=is_warmup,
            completed=not is_warmup,
        )
    )
    db.session.commit()
    return redirect(
        url_for("fitness.log_exercise", session_id=session.id, exercise_id=exercise.id)
    )


@fitness_bp.route("/sets/<int:set_id>/toggle", methods=["POST"])
@login_required
def toggle_set(set_id: int):
    workout_set = _get_own_set(set_id)
    workout_set.completed = not workout_set.completed
    db.session.commit()
    return jsonify({"id": workout_set.id, "completed": workout_set.completed})


@fitness_bp.route("/sets/<int:set_id>/edit", methods=["POST"])
@login_required
def edit_set(set_id: int):
    workout_set = _get_own_set(set_id)
    session_id, exercise_id = workout_set.session_id, workout_set.exercise_id

    try:
        weight, reps, rpe, is_warmup = _parse_set_form()
    except (KeyError, ValueError):
        flash("Enter valid weight, reps, and optional RPE (6–10).", "error")
        return redirect(
            url_for("fitness.log_exercise", session_id=session_id, exercise_id=exercise_id)
        )

    workout_set.weight = weight
    workout_set.reps = reps
    workout_set.rpe = rpe
    workout_set.is_warmup = is_warmup
    db.session.commit()
    flash("Set updated.", "success")
    return redirect(
        url_for("fitness.log_exercise", session_id=session_id, exercise_id=exercise_id)
    )


@fitness_bp.route("/sets/<int:set_id>/delete", methods=["POST"])
@login_required
def delete_set(set_id: int):
    workout_set = _get_own_set(set_id)
    session_id, exercise_id = workout_set.session_id, workout_set.exercise_id
    db.session.delete(workout_set)
    remaining = (
        WorkoutSet.query.filter_by(session_id=session_id, exercise_id=exercise_id)
        .order_by(WorkoutSet.set_number)
        .all()
    )
    for i, s in enumerate(remaining, start=1):
        s.set_number = i
    db.session.commit()
    return redirect(
        url_for("fitness.log_exercise", session_id=session_id, exercise_id=exercise_id)
    )


# ---------------------------------------------------------------------------
# Exercise management
# ---------------------------------------------------------------------------

@fitness_bp.route("/exercises")
@login_required
def exercises():
    items = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    return render_template("fitness/exercises.html", exercises=items)


@fitness_bp.route("/exercises", methods=["POST"])
@login_required
def create_exercise():
    name = request.form.get("name", "").strip()
    muscle_group = request.form.get("muscle_group", "").strip() or "General"
    if not name:
        flash("Exercise name is required.", "error")
        return redirect(request.form.get("next") or url_for("fitness.index"))

    exists = Exercise.query.filter_by(user_id=current_user.id, name=name).first()
    if exists:
        flash(f"“{name}” already exists in your library.", "error")
    else:
        db.session.add(
            Exercise(user_id=current_user.id, name=name, muscle_group=muscle_group)
        )
        db.session.commit()
        flash(f"“{name}” added to your library.", "success")

    next_url = request.form.get("next") or url_for("fitness.index")
    return redirect(next_url)


@fitness_bp.route("/exercises/<int:exercise_id>/edit", methods=["POST"])
@login_required
def edit_exercise(exercise_id: int):
    exercise = _get_own_exercise(exercise_id)
    name = request.form.get("name", "").strip()
    muscle_group = request.form.get("muscle_group", "").strip() or "General"
    if not name:
        flash("Exercise name is required.", "error")
        return redirect(url_for("fitness.exercises"))

    duplicate = Exercise.query.filter(
        Exercise.user_id == current_user.id,
        Exercise.name == name,
        Exercise.id != exercise.id,
    ).first()
    if duplicate:
        flash(f"“{name}” already exists in your library.", "error")
    else:
        exercise.name = name
        exercise.muscle_group = muscle_group
        db.session.commit()
        flash(f"Updated “{name}”.", "success")
    return redirect(url_for("fitness.exercises"))


@fitness_bp.route("/exercises/<int:exercise_id>/delete", methods=["POST"])
@login_required
def delete_exercise(exercise_id: int):
    exercise = _get_own_exercise(exercise_id)
    name = exercise.name
    db.session.delete(exercise)
    db.session.commit()
    flash(f"Deleted “{name}”.", "success")
    return redirect(url_for("fitness.exercises"))


# ---------------------------------------------------------------------------
# Exercise catalog — browse & import built-in library
# ---------------------------------------------------------------------------

@fitness_bp.route("/catalog")
@login_required
def catalog():
    owned = user_exercise_names(current_user.id)
    by_group = {g: catalog_for_muscle_group(g) for g in MUSCLE_GROUPS}
    return render_template(
        "fitness/catalog.html",
        splits=WORKOUT_SPLITS,
        muscle_groups=MUSCLE_GROUPS,
        by_group=by_group,
        owned=owned,
        total_catalog=len(EXERCISE_CATALOG),
        library_count=len(owned),
    )


@fitness_bp.route("/catalog/add", methods=["POST"])
@login_required
def catalog_add():
    name = request.form.get("name", "").strip()
    if not name or catalog_entry(name) is None:
        flash("Unknown exercise.", "error")
    else:
        added, skipped = import_catalog_exercises(current_user.id, [name])
        if added:
            flash(f"Added “{name}” to your library.", "success")
        else:
            flash(f"“{name}” is already in your library.", "error")
    return redirect(request.form.get("next") or url_for("fitness.catalog"))


@fitness_bp.route("/catalog/import-starter", methods=["POST"])
@login_required
def catalog_import_starter():
    added, skipped = import_starter_library(current_user.id)
    if added:
        flash(f"Imported {added} exercises into your library.", "success")
    else:
        flash("Your library already has all starter exercises.", "success")
    return redirect(request.form.get("next") or url_for("fitness.catalog"))


@fitness_bp.route("/catalog/import-split", methods=["POST"])
@login_required
def catalog_import_split():
    split_id = request.form.get("split", "").strip()
    split = get_split(split_id)
    if split is None:
        flash("Unknown workout type.", "error")
        return redirect(url_for("fitness.catalog"))

    added, skipped = import_split_exercises(current_user.id, split_id)
    if added:
        flash(f"Added {added} exercises for {split['name']}.", "success")
    else:
        flash(f"All {split['name']} exercises are already in your library.", "success")
    return redirect(request.form.get("next") or url_for("fitness.catalog"))


# ---------------------------------------------------------------------------
# Stats & personal records
# ---------------------------------------------------------------------------

@fitness_bp.route("/stats")
@login_required
def stats():
    exercises = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    records = [
        {"exercise": ex, "pr": ex.personal_record()}
        for ex in exercises
        if ex.personal_record()
    ]
    records.sort(key=lambda r: r["pr"]["estimated_1rm"], reverse=True)

    week_ago = utcnow() - timedelta(days=7)
    weekly_sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(
            WorkoutSession.finished_at.isnot(None),
            WorkoutSession.started_at >= week_ago,
        )
        .count()
    )
    weekly_volume = (
        db.session.query(
            func.sum(WorkoutSet.weight * WorkoutSet.reps)
        )
        .join(WorkoutSession)
        .filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.finished_at.isnot(None),
            WorkoutSet.completed.is_(True),
            WorkoutSet.is_warmup.is_(False),
            WorkoutSession.started_at >= week_ago,
        )
        .scalar()
    ) or 0.0

    total_sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .count()
    )

    return render_template(
        "fitness/stats.html",
        records=records,
        weekly_sessions=weekly_sessions,
        weekly_volume=round(weekly_volume, 1),
        total_sessions=total_sessions,
        exercise_count=len(exercises),
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@fitness_bp.route("/history")
@login_required
def history():
    sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .all()
    )
    return render_template("fitness/history.html", sessions=sessions)


# ---------------------------------------------------------------------------
# Weight logs — VeSync-ready manual tracking
# ---------------------------------------------------------------------------

@fitness_bp.route("/weight", methods=["GET", "POST"])
@login_required
def weight():
    if request.method == "POST":
        try:
            log_date = date.fromisoformat(request.form["log_date"])
            weight_val = float(request.form["weight"])
            body_fat_raw = request.form.get("body_fat", "").strip()
            body_fat = float(body_fat_raw) if body_fat_raw else None
            if weight_val <= 0:
                raise ValueError
        except (KeyError, ValueError):
            flash("Enter a valid date and weight.", "error")
            return redirect(url_for("fitness.weight"))

        log = WeightLog.query.filter_by(
            user_id=current_user.id, log_date=log_date
        ).first()
        if log:
            log.weight = weight_val
            log.body_fat = body_fat
            flash(f"Updated entry for {log_date.strftime('%b %d')}.", "success")
        else:
            db.session.add(
                WeightLog(
                    user_id=current_user.id,
                    log_date=log_date,
                    weight=weight_val,
                    body_fat=body_fat,
                )
            )
            flash("Weight logged.", "success")
        db.session.commit()
        return redirect(url_for("fitness.weight"))

    logs = (
        WeightLog.query.filter_by(user_id=current_user.id)
        .order_by(WeightLog.log_date.desc())
        .all()
    )
    return render_template("fitness/weight.html", logs=logs, today=date.today())


@fitness_bp.route("/weight/<int:log_id>/delete", methods=["POST"])
@login_required
def delete_weight(log_id: int):
    log = db.session.get(WeightLog, log_id)
    if log is None or log.user_id != current_user.id:
        abort(404)
    db.session.delete(log)
    db.session.commit()
    flash("Weight entry deleted.", "success")
    return redirect(url_for("fitness.weight"))


from . import routes_extra  # noqa: E402,F401
