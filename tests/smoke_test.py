#!/usr/bin/env python3
"""Run catalog/service smoke tests without pytest."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.fitness.catalog import (
    icon_slug_for_exercise,
    is_beginner_exercise,
    display_name_for_exercise,
)


def main() -> int:
    assert icon_slug_for_exercise("Back Squat") == "squat"
    assert icon_slug_for_exercise("Push-ups") == "bodyweight"
    assert is_beginner_exercise("Leg Press")
    assert "sled" in display_name_for_exercise("Leg Press").lower()
    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
