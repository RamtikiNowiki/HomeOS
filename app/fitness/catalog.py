"""Built-in exercise catalog and workout split templates.

Curated from common strength-training programs (push/pull/legs splits).
No external API — works offline on the Pi. Users can still add custom exercises.
"""
from __future__ import annotations

import re
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
    CatalogExercise("Pec Deck Fly Machine", "Chest", "Machine"),
    CatalogExercise("Smith Machine Bench Press", "Chest", "Machine"),
    CatalogExercise("Incline Machine Press", "Chest", "Machine"),
    CatalogExercise("Push-ups", "Chest", "Bodyweight"),
    CatalogExercise("Knee Push-ups", "Chest", "Bodyweight"),
    # Back
    CatalogExercise("Deadlift", "Back", "Barbell"),
    CatalogExercise("Romanian Deadlift", "Back", "Barbell"),
    CatalogExercise("Barbell Row", "Back", "Barbell"),
    CatalogExercise("Pendlay Row", "Back", "Barbell"),
    CatalogExercise("Pull-ups", "Back", "Bodyweight"),
    CatalogExercise("Chin-ups", "Back", "Bodyweight"),
    CatalogExercise("Assisted Pull-up Machine", "Back", "Machine"),
    CatalogExercise("Lat Pulldown", "Back", "Cable"),
    CatalogExercise("Close-Grip Lat Pulldown", "Back", "Cable"),
    CatalogExercise("Seated Cable Row", "Back", "Cable"),
    CatalogExercise("Seated Row Machine", "Back", "Machine"),
    CatalogExercise("T-Bar Row", "Back", "Barbell"),
    CatalogExercise("Dumbbell Row", "Back", "Dumbbell"),
    CatalogExercise("Chest-Supported Row Machine", "Back", "Machine"),
    CatalogExercise("Face Pull", "Back", "Cable"),
    CatalogExercise("Straight-Arm Pulldown", "Back", "Cable"),
    CatalogExercise("Hyperextension", "Back", "Bodyweight"),
    CatalogExercise("Back Extension Machine", "Back", "Machine"),
    # Shoulders
    CatalogExercise("Overhead Press", "Shoulders", "Barbell"),
    CatalogExercise("Seated Dumbbell Press", "Shoulders", "Dumbbell"),
    CatalogExercise("Machine Shoulder Press", "Shoulders", "Machine"),
    CatalogExercise("Smith Machine Shoulder Press", "Shoulders", "Machine"),
    CatalogExercise("Arnold Press", "Shoulders", "Dumbbell"),
    CatalogExercise("Lateral Raise", "Shoulders", "Dumbbell"),
    CatalogExercise("Lateral Raise Machine", "Shoulders", "Machine"),
    CatalogExercise("Front Raise", "Shoulders", "Dumbbell"),
    CatalogExercise("Rear Delt Fly", "Shoulders", "Dumbbell"),
    CatalogExercise("Reverse Pec Deck", "Shoulders", "Machine"),
    CatalogExercise("Upright Row", "Shoulders", "Barbell"),
    CatalogExercise("Cable Lateral Raise", "Shoulders", "Cable"),
    CatalogExercise("Shrugs", "Shoulders", "Barbell"),
    CatalogExercise("Dumbbell Shrugs", "Shoulders", "Dumbbell"),
    # Legs
    CatalogExercise("Back Squat", "Legs", "Barbell"),
    CatalogExercise("Front Squat", "Legs", "Barbell"),
    CatalogExercise("Smith Machine Squat", "Legs", "Machine"),
    CatalogExercise("Leg Press", "Legs", "Machine"),
    CatalogExercise("Hack Squat", "Legs", "Machine"),
    CatalogExercise("Bulgarian Split Squat", "Legs", "Dumbbell"),
    CatalogExercise("Walking Lunge", "Legs", "Dumbbell"),
    CatalogExercise("Step-ups", "Legs", "Dumbbell"),
    CatalogExercise("Leg Extension", "Legs", "Machine"),
    CatalogExercise("Leg Curl", "Legs", "Machine"),
    CatalogExercise("Seated Leg Curl", "Legs", "Machine"),
    CatalogExercise("Hip Thrust", "Legs", "Barbell"),
    CatalogExercise("Hip Thrust Machine", "Legs", "Machine"),
    CatalogExercise("Glute Bridge", "Legs", "Barbell"),
    CatalogExercise("Glute Kickback Machine", "Legs", "Machine"),
    CatalogExercise("Hip Abduction Machine", "Legs", "Machine"),
    CatalogExercise("Hip Adduction Machine", "Legs", "Machine"),
    CatalogExercise("Cable Kickback", "Legs", "Cable"),
    CatalogExercise("Calf Raise", "Legs", "Machine"),
    CatalogExercise("Seated Calf Raise", "Legs", "Machine"),
    CatalogExercise("Goblet Squat", "Legs", "Dumbbell"),
    CatalogExercise("Sumo Squat", "Legs", "Dumbbell"),
    CatalogExercise("Kettlebell Swing", "Legs", "Kettlebell"),
    CatalogExercise("Dumbbell Romanian Deadlift", "Legs", "Dumbbell"),
    # Arms
    CatalogExercise("Barbell Curl", "Arms", "Barbell"),
    CatalogExercise("Dumbbell Curl", "Arms", "Dumbbell"),
    CatalogExercise("Hammer Curl", "Arms", "Dumbbell"),
    CatalogExercise("Preacher Curl", "Arms", "Barbell"),
    CatalogExercise("Preacher Curl Machine", "Arms", "Machine"),
    CatalogExercise("Cable Curl", "Arms", "Cable"),
    CatalogExercise("Incline Dumbbell Curl", "Arms", "Dumbbell"),
    CatalogExercise("Tricep Pushdown", "Arms", "Cable"),
    CatalogExercise("Rope Pushdown", "Arms", "Cable"),
    CatalogExercise("Skull Crushers", "Arms", "Barbell"),
    CatalogExercise("Overhead Tricep Extension", "Arms", "Dumbbell"),
    CatalogExercise("Tricep Extension Machine", "Arms", "Machine"),
    CatalogExercise("Close-Grip Bench Press", "Arms", "Barbell"),
    CatalogExercise("Dips", "Arms", "Bodyweight"),
    CatalogExercise("Assisted Dip Machine", "Arms", "Machine"),
    CatalogExercise("Wrist Curl", "Arms", "Dumbbell"),
    # Core
    CatalogExercise("Plank", "Core", "Bodyweight"),
    CatalogExercise("Side Plank", "Core", "Bodyweight"),
    CatalogExercise("Hanging Leg Raise", "Core", "Bodyweight"),
    CatalogExercise("Crunches", "Core", "Bodyweight"),
    CatalogExercise("Bicycle Crunches", "Core", "Bodyweight"),
    CatalogExercise("Cable Crunch", "Core", "Cable"),
    CatalogExercise("Ab Crunch Machine", "Core", "Machine"),
    CatalogExercise("Ab Wheel Rollout", "Core", "Bodyweight"),
    CatalogExercise("Russian Twist", "Core", "Bodyweight"),
    CatalogExercise("Pallof Press", "Core", "Cable"),
    CatalogExercise("Dead Bug", "Core", "Bodyweight"),
    CatalogExercise("Mountain Climbers", "Core", "Bodyweight"),
)

CATALOG_BY_NAME: dict[str, CatalogExercise] = {e.name: e for e in EXERCISE_CATALOG}

MUSCLE_GROUPS: tuple[str, ...] = (
    "Chest", "Back", "Shoulders", "Legs", "Arms", "Core",
)

# Pixel icons live in static/img/px/{theme}/{slug}.png
# Movement icons (character doing the lift) + equipment fallbacks.
EQUIPMENT_ICONS: dict[str, str] = {
    "Barbell": "barbell",
    "Dumbbell": "dumbbell",
    "Machine": "machine",
    "Cable": "cable",
    "Bodyweight": "bodyweight",
    "Kettlebell": "kettlebell",
}

# Keyword → movement icon, checked in order (first match wins).
# More specific patterns must come before generic ones
# (e.g. "leg curl" before "curl", "leg extension" before arm "extension").
_MOVEMENT_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("leg curl", "leg-press"),
    ("leg extension", "leg-press"),
    ("leg press", "leg-press"),
    ("calf", "leg-press"),
    ("abduction", "leg-press"),
    ("adduction", "leg-press"),
    ("kickback", "leg-press"),
    ("hip thrust", "leg-press"),
    ("glute", "leg-press"),
    ("split squat", "lunge"),
    ("lunge", "lunge"),
    ("step-up", "lunge"),
    ("step up", "lunge"),
    ("squat", "squat"),
    ("deadlift", "deadlift"),
    ("rdl", "deadlift"),
    ("good morning", "deadlift"),
    ("swing", "kettlebell"),
    ("push-up", "bodyweight"),
    ("pushup", "bodyweight"),
    ("push up", "bodyweight"),
    ("bench press", "bench-press"),
    ("chest press", "bench-press"),
    ("incline machine press", "bench-press"),
    ("fly", "bench-press"),
    ("flyes", "bench-press"),
    ("crossover", "bench-press"),
    ("reverse pec deck", "lateral-raise"),
    ("pec deck", "bench-press"),
    ("pull-up", "pullup"),
    ("pullup", "pullup"),
    ("pull up", "pullup"),
    ("chin-up", "pullup"),
    ("chin up", "pullup"),
    ("pulldown", "pullup"),
    ("pullover", "pullup"),
    ("upright row", "lateral-raise"),
    ("row", "row"),
    ("overhead press", "overhead-press"),
    ("shoulder press", "overhead-press"),
    ("arnold", "overhead-press"),
    ("military", "overhead-press"),
    ("lateral raise", "lateral-raise"),
    ("front raise", "lateral-raise"),
    ("rear delt", "lateral-raise"),
    ("face pull", "lateral-raise"),
    ("shrug", "deadlift"),
    ("wrist curl", "curl"),
    ("curl", "curl"),
    ("tricep", "triceps"),
    ("pushdown", "triceps"),
    ("skull", "triceps"),
    ("dip", "triceps"),
    ("close-grip bench", "bench-press"),
    ("plank", "core"),
    ("crunch", "core"),
    ("sit-up", "core"),
    ("leg raise", "core"),
    ("twist", "core"),
    ("rollout", "core"),
    ("dead bug", "core"),
    ("mountain climber", "core"),
    ("pallof", "core"),
    ("hyperextension", "core"),
    ("back extension", "core"),
    ("extension", "triceps"),
)

# Muscle group → sensible default movement icon
_MUSCLE_DEFAULT_ICONS: dict[str, str] = {
    "chest": "bench-press",
    "back": "row",
    "shoulders": "overhead-press",
    "legs": "squat",
    "arms": "curl",
    "core": "core",
}


def icon_slug_for_exercise(name: str, muscle_group: str | None = None) -> str:
    """Pixel-icon slug for an exercise.

    Explicit catalog override first, then movement keywords, muscle default,
    then equipment from the catalog, then bodyweight.
    """
    entry = CATALOG_BY_NAME.get(name)
    if entry and entry.name in CATALOG_ICON_OVERRIDES:
        return CATALOG_ICON_OVERRIDES[entry.name]

    lowered = name.lower()
    for keyword, slug in _MOVEMENT_KEYWORDS:
        if keyword in lowered:
            return slug

    group = muscle_group
    if group is None and entry:
        group = entry.muscle_group
    if group and group.lower() in _MUSCLE_DEFAULT_ICONS:
        return _MUSCLE_DEFAULT_ICONS[group.lower()]

    if entry:
        return EQUIPMENT_ICONS.get(entry.equipment, "bodyweight")
    return "bodyweight"


def equipment_slug_for_exercise(name: str) -> str:
    """Backward-compatible alias — now resolves to movement-aware icons."""
    return icon_slug_for_exercise(name)


# Friendly labels + search aliases for beginners (Aylin-friendly copy)
CATALOG_DISPLAY_NAMES: dict[str, str] = {
    "Leg Press": "Leg press (sled machine)",
    "Hack Squat": "Hack squat (guided machine)",
    "Lat Pulldown": "Lat pulldown (cable machine)",
    "Seated Row Machine": "Seated row (machine)",
    "Machine Chest Press": "Chest press (machine)",
    "Pec Deck Fly Machine": "Pec deck fly (machine)",
    "Leg Extension": "Leg extension (quad machine)",
    "Leg Curl": "Leg curl (hamstring machine)",
    "Assisted Pull-up Machine": "Assisted pull-up (machine)",
    "Assisted Dip Machine": "Assisted dip (machine)",
    "Hip Abduction Machine": "Hip abduction (outer thigh)",
    "Hip Adduction Machine": "Hip adduction (inner thigh)",
    "Glute Kickback Machine": "Glute kickback (machine)",
    "Lateral Raise Machine": "Lateral raise (machine)",
    "Tricep Extension Machine": "Tricep extension (machine)",
    "Ab Crunch Machine": "Ab crunch (machine)",
    "Smith Machine Squat": "Smith machine squat",
    "Smith Machine Bench Press": "Smith machine bench",
    "Romanian Deadlift": "Romanian deadlift (RDL)",
    "Tricep Pushdown": "Tricep pushdown (cable)",
    "Seated Cable Row": "Seated cable row",
}

CATALOG_ALIASES: dict[str, tuple[str, ...]] = {
    "Leg Press": ("Leg sled", "Sled press"),
    "Lat Pulldown": ("Pulldown", "Lat pull"),
    "Romanian Deadlift": ("RDL",),
    "Tricep Pushdown": ("Pushdown", "Cable triceps"),
    "Machine Chest Press": ("Chest press machine",),
    "Assisted Pull-up Machine": ("Assisted pullups",),
    "Hip Thrust Machine": ("Glute machine",),
}

# Explicit icon overrides where keyword matching is ambiguous
CATALOG_ICON_OVERRIDES: dict[str, str] = {
    "Face Pull": "lateral-raise",
    "Shrugs": "deadlift",
    "Dumbbell Shrugs": "deadlift",
    "Upright Row": "lateral-raise",
    "Reverse Pec Deck": "lateral-raise",
    "Rope Pushdown": "triceps",
    "Assisted Dip Machine": "triceps",
    "Wrist Curl": "curl",
    "Kettlebell Swing": "kettlebell",
    "Hyperextension": "core",
    "Back Extension Machine": "core",
    "Straight-Arm Pulldown": "pullup",
    "Close-Grip Lat Pulldown": "pullup",
    "Chest-Supported Row Machine": "row",
    "Cable Kickback": "leg-press",
    "Hip Thrust Machine": "leg-press",
    "Glute Kickback Machine": "leg-press",
    "Preacher Curl Machine": "curl",
}

# Machine-first + easy cable/bodyweight picks for beginner import
BEGINNER_EXERCISES: tuple[str, ...] = tuple(
    dict.fromkeys(
        e.name
        for e in EXERCISE_CATALOG
        if e.equipment == "Machine"
        or e.name in (
            "Lat Pulldown",
            "Seated Cable Row",
            "Tricep Pushdown",
            "Cable Curl",
            "Push-ups",
            "Knee Push-ups",
            "Plank",
            "Crunches",
            "Goblet Squat",
            "Dumbbell Bench Press",
            "Dumbbell Curl",
            "Hammer Curl",
            "Walking Lunge",
        )
    )
)

# Shared machine-friendly routines (seeded for Aylin)
BEGINNER_ROUTINES: tuple[dict, ...] = (
    {
        "name": "Aylin — Easy Leg Day",
        "exercises": (
            "Leg Press",
            "Leg Extension",
            "Leg Curl",
            "Hip Abduction Machine",
            "Seated Calf Raise",
        ),
    },
    {
        "name": "Aylin — Upper Machines",
        "exercises": (
            "Machine Chest Press",
            "Lat Pulldown",
            "Seated Row Machine",
            "Machine Shoulder Press",
            "Tricep Pushdown",
        ),
    },
)


def display_name_for_exercise(name: str) -> str:
    return CATALOG_DISPLAY_NAMES.get(name, name)


def aliases_for_exercise(name: str) -> tuple[str, ...]:
    return CATALOG_ALIASES.get(name, ())


def is_beginner_exercise(name: str) -> bool:
    return name in BEGINNER_EXERCISES


def equipment_for_exercise(name: str) -> str | None:
    entry = CATALOG_BY_NAME.get(name)
    return entry.equipment if entry else None


def is_barbell_exercise(name: str) -> bool:
    eq = equipment_for_exercise(name)
    if eq == "Barbell":
        return True
    lowered = name.lower()
    return "barbell" in lowered or "bench press" in lowered and "machine" not in lowered

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


def _contains_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


def infer_split_key_from_name(name: str) -> str | None:
    """Guess a split template from a free-form session name (e.g. 'Legs' → legs)."""
    text = name.strip().lower()
    if not text:
        return None

    slug = text.replace("-", " ").replace("_", " ")

    for split_id in WORKOUT_SPLITS:
        sid = split_id.replace("_", " ")
        if sid == slug or split_id == slug.replace(" ", "_"):
            return split_id

    for split_id, split in WORKOUT_SPLITS.items():
        split_name = split["name"].lower()
        if split_name in slug or slug in split_name:
            return split_id

    rules: list[tuple[str, tuple[str, ...]]] = [
        ("full_body", ("full body", "fullbody", "whole body")),
        ("upper", ("upper body", "upper day")),
        ("lower", ("lower body", "lower day")),
        ("legs", ("leg day", "legday", "legs", "leg workout", "quads", "hamstrings", "glutes")),
        ("push", ("push day", "pushday", "triceps", "tricep")),
        ("pull", ("pull day", "pullday", "biceps", "bicep")),
        ("chest", ("chest day",)),
        ("back", ("back day",)),
        ("shoulders", ("shoulder day", "shoulders", "delts", "delt")),
        ("arms", ("arm day", "arms day")),
    ]
    for split_id, keywords in rules:
        for kw in keywords:
            if kw in slug:
                return split_id

    for split_id, keywords in (
        ("legs", ("leg",)),
        ("push", ("push",)),
        ("pull", ("pull",)),
        ("chest", ("chest",)),
        ("back", ("back",)),
        ("shoulders", ("shoulder",)),
        ("arms", ("arms",)),
        ("upper", ("upper",)),
        ("lower", ("lower",)),
    ):
        for kw in keywords:
            if _contains_word(slug, kw):
                return split_id

    return None


def muscle_groups_for_split(split_id: str) -> set[str]:
    """Primary muscle groups targeted by a split template."""
    split = get_split(split_id)
    if not split:
        return set()
    groups: set[str] = set()
    for ex_name in split["exercises"]:
        entry = catalog_entry(ex_name)
        if entry:
            groups.add(entry.muscle_group)
    return groups
