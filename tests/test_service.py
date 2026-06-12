"""Fitness service helpers."""
from app import create_app
from app.extensions import db
from app.models import Exercise, User, WorkoutSession, WorkoutSet
from app.fitness.service import check_set_beats_pr, workout_streak_stats


def test_check_set_beats_pr_first_set():
    app = create_app()
    with app.app_context():
        user = User(username="test_pr", display_name="Test", accent="indigo")
        user.set_password("x")
        db.session.add(user)
        db.session.flush()
        ex = Exercise(user_id=user.id, name="Test Curl", muscle_group="Arms")
        db.session.add(ex)
        db.session.commit()
        pr = check_set_beats_pr(ex, 50.0, 10, False)
        assert pr is not None
        assert pr["estimated_1rm"] > 0


def test_warmup_not_pr():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username="test_pr").first()
        if user is None:
            return
        ex = Exercise.query.filter_by(user_id=user.id).first()
        assert check_set_beats_pr(ex, 100.0, 5, True) is None
