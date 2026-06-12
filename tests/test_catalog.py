"""Catalog icon mapping and beginner metadata."""
from app.fitness.catalog import (
    BEGINNER_EXERCISES,
    display_name_for_exercise,
    icon_slug_for_exercise,
    is_beginner_exercise,
    is_barbell_exercise,
)


def test_squat_maps_to_squat_icon():
    assert icon_slug_for_exercise("Back Squat") == "squat"
    assert icon_slug_for_exercise("Goblet Squat") == "squat"


def test_pushup_not_squat():
    assert icon_slug_for_exercise("Push-ups") == "bodyweight"


def test_leg_press_machine_icon():
    assert icon_slug_for_exercise("Leg Press") == "leg-press"


def test_face_pull_override():
    assert icon_slug_for_exercise("Face Pull") == "lateral-raise"


def test_display_name_friendly():
    assert "sled" in display_name_for_exercise("Leg Press").lower()


def test_beginner_machines():
    assert is_beginner_exercise("Leg Press")
    assert is_beginner_exercise("Machine Chest Press")
    assert not is_beginner_exercise("Back Squat")
    assert len(BEGINNER_EXERCISES) >= 20


def test_barbell_detection():
    assert is_barbell_exercise("Barbell Bench Press")
    assert not is_barbell_exercise("Leg Press")
