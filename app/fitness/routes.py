from datetime import datetime, date, timedelta
import csv
import io

from flask import abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Exercise, WeightLog, WorkoutSession, WorkoutSet, WorkoutRoutine, WorkoutRoutineExercise, UserProgramDay, utcnow
from .plates import calculate_plates
from ..units import DEFAULT_BAR_LB
from . import fitness_bp
from .catalog import (
    EXERCISE_CATALOG,
    MUSCLE_GROUPS,
    STARTER_EXERCISES,
    WORKOUT_SPLITS,
    BEGINNER_EXERCISES,
    catalog_entry,
    catalog_for_muscle_group,
    display_name_for_exercise,
    get_split,
    icon_slug_for_exercise,
    infer_split_key_from_name,
    is_barbell_exercise,
    is_beginner_exercise,
)
from .service import (
    check_set_beats_pr,
    get_program_week,
    import_beginner_library,
    import_catalog_exercises,
    import_split_exercises,
    import_starter_library,
    last_logged_exercise,
    next_exercise_in_session,
    resolve_split_exercises,
    resolved_split_key,
    routine_progress,
    session_plan_progress,
    sort_exercises_for_session,
    split_progress,
    suggest_next_exercise,
    default_muscle_filter_for_session,
    user_exercise_names,
    workout_streak_stats,
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


def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best_match(["application/json", "text/html"])
        == "application/json"
    )


def _plan_tray_payload(session: WorkoutSession, current_exercise_id: int | None = None) -> list[dict]:
    """Workout-plan exercises for the collapsed log-sheet tray (in plan order)."""
    progress = session_plan_progress(session)
    if not progress:
        return []
    theme = "pink" if getattr(current_user, "accent", None) == "pink" else "blue"
    done_ids = {ex.id for ex in progress.get("done", [])}
    skipped = progress.get("skipped", [])
    remaining = progress.get("remaining", [])
    next_id = remaining[0].id if remaining else None
    tray = []
    for ex in progress.get("recommended", []):
        if ex in skipped:
            continue
        slug = icon_slug_for_exercise(ex.name, ex.muscle_group)
        tray.append({
            "id": ex.id,
            "name": ex.name,
            "display_name": display_name_for_exercise(ex.name),
            "icon": f"img/px/{theme}/{slug}.png",
            "url": url_for("fitness.log_exercise", session_id=session.id, exercise_id=ex.id),
            "priority": ex.id == next_id and ex.id != current_exercise_id,
            "current": ex.id == current_exercise_id,
            "done": ex.id in done_ids,
        })
    return tray


def _set_to_json(workout_set: WorkoutSet) -> dict:
    return {
        "id": workout_set.id,
        "set_number": workout_set.set_number,
        "weight": workout_set.weight,
        "reps": workout_set.reps,
        "rpe": workout_set.rpe,
        "is_warmup": workout_set.is_warmup,
        "completed": workout_set.completed,
        "toggle_url": url_for("fitness.toggle_set", set_id=workout_set.id),
        "edit_url": url_for("fitness.edit_set", set_id=workout_set.id),
        "delete_url": url_for("fitness.delete_set", set_id=workout_set.id),
    }


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
    routines = (
        WorkoutRoutine.query.filter_by(user_id=current_user.id)
        .order_by(WorkoutRoutine.name)
        .all()
    )
    progress = None
    next_exercise = None
    last_exercise = None
    if active_session:
        progress = session_plan_progress(active_session)
        last_exercise = last_logged_exercise(active_session)
        next_exercise = suggest_next_exercise(active_session)

    week = get_program_week(current_user.id)
    today_program = week[datetime.now().weekday()]
    streak = workout_streak_stats(current_user.id)

    return render_template(
        "fitness/index.html",
        active_session=active_session,
        exercises=exercises,
        recent_sessions=recent_sessions,
        latest_weight=latest_weight,
        splits=WORKOUT_SPLITS,
        muscle_groups=MUSCLE_GROUPS,
        starter_count=len(STARTER_EXERCISES),
        routines=routines,
        progress=progress,
        next_exercise=next_exercise,
        last_exercise=last_exercise,
        today_program=today_program,
        streak=streak,
    )


@fitness_bp.route("/tools")
@login_required
def tools():
    return render_template("fitness/tools.html")


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
    use_split_template = bool(split_id)

    name = request.form.get("name", "").strip()
    if not name:
        name = split["name"] if split else datetime.now().strftime("%A Session")

    focus = request.form.get("focus", "").strip() or None
    if not split_id and focus:
        split_id = focus
    elif not split_id and name:
        inferred = infer_split_key_from_name(name)
        if inferred:
            split_id = inferred

    if use_split_template and split_id:
        added, _ = import_split_exercises(current_user.id, split_id)
        if added:
            flash(f"Added {added} exercises to your library.", "success")
    elif split_id and split:
        # Ad-hoc "Legs" etc. — ensure split exercises exist in library for the picker
        added, _ = import_split_exercises(current_user.id, split_id)
        if added:
            flash(f"Added {added} {split['name'].lower()} exercises to your library.", "success")

    session = WorkoutSession(
        user_id=current_user.id,
        name=name,
        workout_type=split_id,
        use_split_template=use_split_template,
    )
    db.session.add(session)
    db.session.commit()
    if use_split_template and split:
        flash("Session started — follow the suggested exercises below.", "success")
    elif split_id and split:
        flash(f"Session started — tap + to add {split['name'].lower()} exercises to your workout.", "success")
    else:
        flash("Session started — tap + to add exercises to your workout.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>")
@login_required
def session_detail(session_id: int):
    session = _get_own_session(session_id)
    exercises = sort_exercises_for_session(
        session,
        Exercise.query.filter_by(user_id=current_user.id).all(),
    )
    performed = [
        {"exercise": ex, "sets": session.sets_for_exercise(ex.id)}
        for ex in session.exercises_performed
    ]
    progress = session_plan_progress(session)
    split_key = session.workout_type
    split_info = get_split(split_key) if split_key else None
    planned_id_set = set(session.planned_ids())
    recommended_ids = {ex.id for ex in progress["recommended"]} if progress else planned_id_set
    other_exercises = [ex for ex in exercises if ex.id not in recommended_ids]
    next_exercise = suggest_next_exercise(session) if session.is_active else None
    is_ad_hoc = not session.use_split_template and not session.routine_id
    suggested_exercises = []
    if is_ad_hoc and split_key and session.is_active:
        import_split_exercises(session.user_id, split_key)
        in_plan = planned_id_set | recommended_ids
        suggested_exercises = [
            ex for ex in resolve_split_exercises(session.user_id, split_key)
            if ex.id not in in_plan
        ]
    return render_template(
        "fitness/session.html",
        session=session,
        exercises=exercises,
        performed=performed,
        progress=progress,
        split_info=split_info,
        other_exercises=other_exercises,
        suggested_exercises=suggested_exercises,
        planned_id_set=planned_id_set,
        is_ad_hoc=is_ad_hoc,
        default_muscle_filter=default_muscle_filter_for_session(session),
        muscle_groups=MUSCLE_GROUPS,
        next_exercise=next_exercise,
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
    return redirect(url_for("fitness.session_summary", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>/summary")
@login_required
def session_summary(session_id: int):
    session = _get_own_session(session_id)
    if session.is_active:
        return redirect(url_for("fitness.session_detail", session_id=session.id))
    from .service import session_summary as build_summary
    summary = build_summary(session)
    return render_template(
        "fitness/session_summary.html",
        session=session,
        summary=summary,
    )


@fitness_bp.route("/session/<int:session_id>/notes", methods=["POST"])
@login_required
def update_session_notes(session_id: int):
    session = _get_own_session(session_id)
    notes = request.form.get("notes", "").strip() or None
    session.notes = notes
    db.session.commit()
    if _wants_json():
        return jsonify({"ok": True, "notes": notes or ""})
    flash("Session notes saved.", "success")
    return redirect(url_for("fitness.session_detail", session_id=session.id))


@fitness_bp.route("/session/<int:session_id>/discard", methods=["POST"])
@login_required
def discard_session(session_id: int):
    """Abandon an in-progress workout without saving to history."""
    session = _get_own_session(session_id)
    if not session.is_active:
        flash("This session is already finished.", "error")
        return redirect(url_for("fitness.session_detail", session_id=session.id))
    name = session.name
    set_count = session.total_sets
    db.session.delete(session)
    db.session.commit()
    flash(
        f"Discarded “{name}”" + (f" ({set_count} sets removed)." if set_count else "."),
        "success",
    )
    return redirect(url_for("fitness.index"))


def _redirect_after_plan_change(session_id: int):
    """Return to the page the user came from, or the session view."""
    target = request.form.get("next") or request.referrer
    if target:
        return redirect(target)
    return redirect(url_for("fitness.session_detail", session_id=session_id))


@fitness_bp.route("/session/<int:session_id>/plan/add/<int:exercise_id>", methods=["POST"])
@login_required
def add_to_session_plan(session_id: int, exercise_id: int):
    """Add an exercise to the user's on-the-fly workout queue."""
    session = _get_own_session(session_id)
    if not session.is_active:
        flash("This session is already finished.", "error")
        return _redirect_after_plan_change(session_id)
    exercise = _get_own_exercise(exercise_id)
    if exercise.id in session.planned_ids():
        flash(f"“{exercise.name}” is already in your workout.", "info")
        return _redirect_after_plan_change(session_id)
    session.add_planned_exercise(exercise.id)
    db.session.commit()
    if _wants_json():
        current_id = request.form.get("current_exercise_id", type=int)
        return jsonify({
            "ok": True,
            "exercise": {"id": exercise.id, "name": exercise.name},
            "plan": _plan_tray_payload(session, current_id),
        })
    flash(f"Added “{exercise.name}” to your workout.", "success")
    return _redirect_after_plan_change(session_id)


@fitness_bp.route("/session/<int:session_id>/plan/remove/<int:exercise_id>", methods=["POST"])
@login_required
def remove_from_session_plan(session_id: int, exercise_id: int):
    """Remove an exercise from the on-the-fly queue (before logging sets)."""
    session = _get_own_session(session_id)
    if not session.is_active:
        flash("This session is already finished.", "error")
        return _redirect_after_plan_change(session_id)
    exercise = _get_own_exercise(exercise_id)
    if exercise.id not in session.planned_ids():
        flash(f"“{exercise.name}” isn't in your workout list.", "error")
        return _redirect_after_plan_change(session_id)
    if session.sets_for_exercise(exercise.id):
        flash(f"“{exercise.name}” already has logged sets — finish logging or delete sets first.", "error")
        return _redirect_after_plan_change(session_id)
    session.remove_planned_exercise(exercise.id)
    db.session.commit()
    if _wants_json():
        current_id = request.form.get("current_exercise_id", type=int)
        return jsonify({
            "ok": True,
            "exercise": {"id": exercise.id, "name": exercise.name},
            "plan": _plan_tray_payload(session, current_id),
        })
    flash(f"Removed “{exercise.name}” from your workout.", "success")
    return _redirect_after_plan_change(session_id)


@fitness_bp.route("/session/<int:session_id>/skip/<int:exercise_id>", methods=["POST"])
@login_required
def skip_plan_exercise(session_id: int, exercise_id: int):
    """Skip a planned exercise for this session only (machine taken, swapping order, etc.)."""
    session = _get_own_session(session_id)
    if not session.is_active:
        flash("This session is already finished.", "error")
        return redirect(url_for("fitness.session_detail", session_id=session.id))
    exercise = _get_own_exercise(exercise_id)
    if session.sets_for_exercise(exercise.id):
        flash(f"“{exercise.name}” already has logged sets — finish or delete them first.", "error")
        return _redirect_after_plan_change(session.id)
    session.skip_exercise(exercise.id)
    db.session.commit()
    flash(f"Skipped “{exercise.name}” for this workout.", "success")
    return _redirect_after_plan_change(session.id)


@fitness_bp.route("/session/<int:session_id>/unskip/<int:exercise_id>", methods=["POST"])
@login_required
def unskip_plan_exercise(session_id: int, exercise_id: int):
    session = _get_own_session(session_id)
    if not session.is_active:
        flash("This session is already finished.", "error")
        return redirect(url_for("fitness.session_detail", session_id=session.id))
    exercise = _get_own_exercise(exercise_id)
    session.unskip_exercise(exercise.id)
    db.session.commit()
    flash(f"“{exercise.name}” restored to your plan.", "success")
    return _redirect_after_plan_change(session.id)


@fitness_bp.route("/session/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_session(session_id: int):
    session = _get_own_session(session_id)
    was_active = session.is_active
    db.session.delete(session)
    db.session.commit()
    flash("Session deleted.", "success")
    if was_active:
        return redirect(url_for("fitness.index"))
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
    plate_hint = calculate_plates(float(prefill["weight"]), DEFAULT_BAR_LB) if prefill.get("weight") else None
    progress = session_plan_progress(session)
    all_exercises = sort_exercises_for_session(
        session,
        Exercise.query.filter_by(user_id=current_user.id).all(),
    )
    plan_ids = {ex.id for ex in progress["recommended"]} if progress else set()
    extra_exercises = [ex for ex in all_exercises if ex.id not in plan_ids and ex.id != exercise.id]
    is_ad_hoc = not session.use_split_template and not session.routine_id
    planned_id_set = set(session.planned_ids())

    tray_exercises = _plan_tray_payload(session, exercise.id)
    next_ex_icon = None
    if nxt:
        slug = icon_slug_for_exercise(nxt.name, nxt.muscle_group)
        theme = "pink" if getattr(current_user, "accent", None) == "pink" else "blue"
        next_ex_icon = f"img/px/{theme}/{slug}.png"

    return render_template(
        "fitness/log_exercise.html",
        session=session,
        exercise=exercise,
        current_sets=current_sets,
        previous=previous,
        prefill=prefill,
        next_exercise=nxt,
        next_exercise_icon=next_ex_icon,
        plate_hint=plate_hint,
        is_barbell=is_barbell_exercise(exercise.name),
        exercise_display_name=display_name_for_exercise(exercise.name),
        progress=progress,
        extra_exercises=extra_exercises,
        tray_exercises=tray_exercises,
        is_ad_hoc=is_ad_hoc,
        planned_id_set=planned_id_set,
        default_muscle_filter=default_muscle_filter_for_session(session),
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
    workout_set = WorkoutSet(
        session_id=session.id,
        exercise_id=exercise.id,
        set_number=next_number,
        reps=reps,
        weight=weight,
        rpe=rpe,
        is_warmup=is_warmup,
        completed=not is_warmup,
    )
    db.session.add(workout_set)
    db.session.commit()

    pr_hit = check_set_beats_pr(exercise, weight, reps, is_warmup)

    if _wants_json():
        plate_hint = calculate_plates(weight, DEFAULT_BAR_LB)
        return jsonify({
            "set": _set_to_json(workout_set),
            "set_count": len(session.sets_for_exercise(exercise.id)),
            "plate_hint": plate_hint,
            "prefill": {"weight": weight, "reps": reps, "rpe": rpe or ""},
            "pr": pr_hit,
        })

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
    if _wants_json():
        return jsonify({"ok": True, "set_count": len(remaining)})
    return redirect(
        url_for("fitness.log_exercise", session_id=session_id, exercise_id=exercise_id)
    )


# ---------------------------------------------------------------------------
# Exercise management
# ---------------------------------------------------------------------------

@fitness_bp.route("/exercises/search")
@login_required
def search_exercises():
    """JSON search across the user's exercise library."""
    q = request.args.get("q", "").strip().lower()
    items = (
        Exercise.query.filter_by(user_id=current_user.id)
        .order_by(Exercise.muscle_group, Exercise.name)
        .all()
    )
    if q:
        items = [
            ex
            for ex in items
            if q in ex.name.lower() or q in ex.muscle_group.lower()
        ]
    return jsonify([
        {
            "id": ex.id,
            "name": ex.name,
            "muscle_group": ex.muscle_group,
            "log_url": url_for(
                "fitness.quick_start_exercise", exercise_id=ex.id
            ),
        }
        for ex in items[:30]
    ])


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
    session_id = request.form.get("session_id", type=int)
    if exists:
        flash(f"“{name}” already exists in your library.", "error")
        if session_id:
            session = db.session.get(WorkoutSession, session_id)
            if session and session.user_id == current_user.id and session.is_active:
                return redirect(
                    url_for(
                        "fitness.log_exercise",
                        session_id=session.id,
                        exercise_id=exists.id,
                    )
                )
        return redirect(request.form.get("next") or url_for("fitness.index"))

    exercise = Exercise(user_id=current_user.id, name=name, muscle_group=muscle_group)
    db.session.add(exercise)
    db.session.commit()
    flash(f"“{name}” added to your library.", "success")
    if session_id:
        session = _get_own_session(session_id)
        if session.is_active:
            return redirect(
                url_for(
                    "fitness.log_exercise",
                    session_id=session.id,
                    exercise_id=exercise.id,
                )
            )
    return redirect(request.form.get("next") or url_for("fitness.index"))


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
        beginner_count=len(BEGINNER_EXERCISES),
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


@fitness_bp.route("/catalog/import-beginner", methods=["POST"])
@login_required
def catalog_import_beginner():
    added, skipped = import_beginner_library(current_user.id)
    if added:
        flash(f"Imported {added} beginner-friendly exercises (mostly machines).", "success")
    else:
        flash("Your library already has all beginner exercises.", "success")
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

    from .service import (
        longest_workout_streak,
        weekly_volume_by_muscle,
        days_since_last_focus,
    )
    streak = workout_streak_stats(current_user.id)
    insights = {
        "longest_streak": longest_workout_streak(current_user.id),
        "current_streak": streak["day_streak"],
        "muscle_volume": weekly_volume_by_muscle(current_user.id),
        "days_since_legs": days_since_last_focus(current_user.id, "legs"),
        "days_since_push": days_since_last_focus(current_user.id, "push"),
        "days_since_pull": days_since_last_focus(current_user.id, "pull"),
    }

    return render_template(
        "fitness/stats.html",
        records=records,
        weekly_sessions=weekly_sessions,
        weekly_volume=round(weekly_volume, 1),
        total_sessions=total_sessions,
        exercise_count=len(exercises),
        insights=insights,
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


@fitness_bp.route("/history/export.csv")
@login_required
def history_export_csv():
    sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .filter(WorkoutSession.finished_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["session_date", "session_name", "exercise", "muscle_group", "set", "weight_lb", "reps", "rpe", "warmup"])
    for session in sessions:
        for ws in session.sets.order_by(WorkoutSet.id).all():
            writer.writerow([
                session.started_at.strftime("%Y-%m-%d"),
                session.name,
                ws.exercise.name if ws.exercise else "",
                ws.exercise.muscle_group if ws.exercise else "",
                ws.set_number,
                ws.weight,
                ws.reps,
                ws.rpe or "",
                "yes" if ws.is_warmup else "no",
            ])
    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="workout-history.csv"'
    return resp


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
