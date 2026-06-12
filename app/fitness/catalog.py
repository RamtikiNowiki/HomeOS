"""Built-in exercise catalog and workout split templates.

Curated from common strength-training programs (push/pull/legs splits).
No external API — works offline on the Pi. Users can still add custom exercises.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogExercise:
    name: str
    muscle_group: str
    equipment: str = "Barbell"


# ---------------------------------------------------------------------------
# Full exercise catalog (~60 common lifts)
# ---------------------------------------------------------------------------

EXERCISE_CATALOG: tuple[CatalogExercise, ...] = (
    # Chest
    CatalogExercise("Barbell Bench Press", "Chest", "Barbell"),
    CatalogExercise("Incline Barbell Bench Press", "Chest", "Barbell"),
    CatalogExercise("Decline Barbell Bench Press", "Chest", "Barbell"),
    CatalogExercise("Dumbbell Bench Press", "Chest", "Dumbbell"),
    CatalogExercise("Incline Dumbbell Press", "Chest", "Dumbbell"),
    CatalogExercise("Dumbbell Flyes", "Chest", "Dumbbell"),
    CatalogExercise("Cable Crossover", "Chest", "Cable"),
    CatalogExercise("Chest Dip", "Chest", "Bodyweight"),
    CatalogExercise("Machine Chest Press", "Chest", "Machine"),
    CatalogExercise("Push-ups", "Chest", "Bodyweight"),
    # Back
    CatalogExercise("Deadlift", "Back", "Barbell"),
    CatalogExercise("Romanian Deadlift", "Back", "Barbell"),
    CatalogExercise("Barbell Row", "Back", "Barbell"),
    CatalogExercise("Pendlay Row", "Back", "Barbell"),
    CatalogExercise("Pull-ups", "Back", "Bodyweight"),
    CatalogExercise("Chin-ups", "Back", "Bodyweight"),
    CatalogExercise("Lat Pulldown", "Back", "Cable"),
    CatalogExercise("Seated Cable Row", "Back", "Cable"),
    CatalogExercise("T-Bar Row", "Back", "Barbell"),
    CatalogExercise("Dumbbell Row", "Back", "Dumbbell"),
    CatalogExercise("Face Pull", "Back", "Cable"),
    CatalogExercise("Hyperextension", "Back", "Bodyweight"),
    # Shoulders
    CatalogExercise("Overhead Press", "Shoulders", "Barbell"),
    CatalogExercise("Seated Dumbbell Press", "Shoulders", "Dumbbell"),
    CatalogExercise("Arnold Press", "Shoulders", "Dumbbell"),
    CatalogExercise("Lateral Raise", "Shoulders", "Dumbbell"),
    CatalogExercise("Front Raise", "Shoulders", "Dumbbell"),
    CatalogExercise("Rear Delt Fly", "Shoulders", "Dumbbell"),
    CatalogExercise("Upright Row", "Shoulders", "Barbell"),
    CatalogExercise("Cable Lateral Raise", "Shoulders", "Cable"),
    CatalogExercise("Shrugs", "Shoulders", "Barbell"),
    # Legs
    CatalogExercise("Back Squat", "Legs", "Barbell"),
    CatalogExercise("Front Squat", "Legs", "Barbell"),
    CatalogExercise("Leg Press", "Legs", "Machine"),
    CatalogExercise("Hack Squat", "Legs", "Machine"),
    CatalogExercise("Bulgarian Split Squat", "Legs", "Dumbbell"),
    CatalogExercise("Walking Lunge", "Legs", "Dumbbell"),
    CatalogExercise("Leg Extension", "Legs", "Machine"),
    CatalogExercise("Leg Curl", "Legs", "Machine"),
    CatalogExercise("Hip Thrust", "Legs", "Barbell"),
    CatalogExercise("Glute Bridge", "Legs", "Barbell"),
    CatalogExercise("Calf Raise", "Legs", "Machine"),
    CatalogExercise("Seated Calf Raise", "Legs", "Machine"),
    CatalogExercise("Goblet Squat", "Legs", "Dumbbell"),
    # Arms
    CatalogExercise("Barbell Curl", "Arms", "Barbell"),
    CatalogExercise("Dumbbell Curl", "Arms", "Dumbbell"),
    CatalogExercise("Hammer Curl", "Arms", "Dumbbell"),
    CatalogExercise("Preacher Curl", "Arms", "Barbell"),
    CatalogExercise("Cable Curl", "Arms", "Cable"),
    CatalogExercise("Tricep Pushdown", "Arms", "Cable"),
    CatalogExercise("Skull Crushers", "Arms", "Barbell"),
    CatalogExercise("Overhead Tricep Extension", "Arms", "Dumbbell"),
    CatalogExercise("Close-Grip Bench Press", "Arms", "Barbell"),
    CatalogExercise("Dips", "Arms", "Bodyweight"),
    # Core
    CatalogExercise("Plank", "Core", "Bodyweight"),
    CatalogExercise("Hanging Leg Raise", "Core", "Bodyweight"),
    CatalogExercise("Cable Crunch", "Core", "Cable"),
    CatalogExercise("Ab Wheel Rollout", "Core", "Bodyweight"),
    CatalogExercise("Russian Twist", "Core", "Bodyweight"),
    CatalogExercise("Pallof Press", "Core", "Cable"),
)

CATALOG_BY_NAME: dict[str, CatalogExercise] = {e.name: e for e in EXERCISE_CATALOG}

MUSCLE_GROUPS: tuple[str, ...] = (
    "Chest", "Back", "Shoulders", "Legs", "Arms", "Core",
)

# ---------------------------------------------------------------------------
# Workout split templates
# ---------------------------------------------------------------------------

WORKOUT_SPLITS: dict[str, dict] = {
    "push": {
        "name": "Push Day",
        "description": "Chest, shoulders & triceps",
        "color": "neon",
        "exercises": [
            "Barbell Bench Press",
            "Incline Dumbbell Press",
            "Overhead Press",
            "Lateral Raise",
            "Tricep Pushdown",
            "Close-Grip Bench Press",
        ],
    },
    "pull": {
        "name": "Pull Day",
        "description": "Back & biceps",
        "color": "pulse",
        "exercises": [
            "Deadlift",
            "Pull-ups",
            "Barbell Row",
            "Lat Pulldown",
            "Face Pull",
            "Barbell Curl",
            "Hammer Curl",
        ],
    },
    "legs": {
        "name": "Leg Day",
        "description": "Quads, hamstrings & glutes",
        "color": "emerald",
        "exercises": [
            "Back Squat",
            "Romanian Deadlift",
            "Leg Press",
            "Leg Curl",
            "Leg Extension",
            "Hip Thrust",
            "Calf Raise",
        ],
    },
    "chest": {
        "name": "Chest Day",
        "description": "All chest-focused work",
        "color": "neon",
        "exercises": [
            "Barbell Bench Press",
            "Incline Barbell Bench Press",
            "Dumbbell Bench Press",
            "Incline Dumbbell Press",
            "Dumbbell Flyes",
            "Cable Crossover",
            "Chest Dip",
        ],
    },
    "back": {
        "name": "Back Day",
        "description": "Thickness & width",
        "color": "pulse",
        "exercises": [
            "Deadlift",
            "Pull-ups",
            "Barbell Row",
            "Lat Pulldown",
            "Seated Cable Row",
            "Face Pull",
            "Hyperextension",
        ],
    },
    "shoulders": {
        "name": "Shoulder Day",
        "description": "Delts from every angle",
        "color": "amber",
        "exercises": [
            "Overhead Press",
            "Seated Dumbbell Press",
            "Lateral Raise",
            "Front Raise",
            "Rear Delt Fly",
            "Face Pull",
            "Shrugs",
        ],
    },
    "arms": {
        "name": "Arms Day",
        "description": "Biceps & triceps",
        "color": "rose",
        "exercises": [
            "Barbell Curl",
            "Hammer Curl",
            "Preacher Curl",
            "Tricep Pushdown",
            "Skull Crushers",
            "Overhead Tricep Extension",
            "Dips",
        ],
    },
    "upper": {
        "name": "Upper Body",
        "description": "Full upper in one session",
        "color": "pulse",
        "exercises": [
            "Barbell Bench Press",
            "Barbell Row",
            "Overhead Press",
            "Lat Pulldown",
            "Lateral Raise",
            "Barbell Curl",
            "Tricep Pushdown",
        ],
    },
    "lower": {
        "name": "Lower Body",
        "description": "Full lower in one session",
        "color": "emerald",
        "exercises": [
            "Back Squat",
            "Romanian Deadlift",
            "Leg Press",
            "Leg Curl",
            "Hip Thrust",
            "Calf Raise",
        ],
    },
    "full_body": {
        "name": "Full Body",
        "description": "Compound lifts, whole body",
        "color": "neon",
        "exercises": [
            "Back Squat",
            "Barbell Bench Press",
            "Deadlift",
            "Overhead Press",
            "Barbell Row",
            "Pull-ups",
        ],
    },
}

# Starter set for new profiles (covers all major patterns)
STARTER_EXERCISES: tuple[str, ...] = tuple(
    dict.fromkeys(
        ex.name
        for split in WORKOUT_SPLITS.values()
        for ex in (CATALOG_BY_NAME[n] for n in split["exercises"] if n in CATALOG_BY_NAME)
    )
)


def get_split(split_id: str) -> dict | None:
    return WORKOUT_SPLITS.get(split_id)


def get_split_exercise_names(split_id: str) -> list[str]:
    split = get_split(split_id)
    return list(split["exercises"]) if split else []


def catalog_for_muscle_group(group: str) -> list[CatalogExercise]:
    return [e for e in EXERCISE_CATALOG if e.muscle_group == group]


def catalog_entry(name: str) -> CatalogExercise | None:
    return CATALOG_BY_NAME.get(name)
