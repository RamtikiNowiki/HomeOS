"""Barbell plate calculator — metric (kg) plates."""

DEFAULT_PLATES = (25, 20, 15, 10, 5, 2.5, 1.25)
DEFAULT_BAR = 20.0


def calculate_plates(
    target_weight: float,
    bar_weight: float = DEFAULT_BAR,
    available: tuple[float, ...] = DEFAULT_PLATES,
) -> dict:
    """Return plates per side to reach target weight (or closest possible)."""
    if target_weight <= 0:
        return {"error": "Enter a positive weight.", "per_side": [], "achieved": 0.0}

    if target_weight < bar_weight:
        return {
            "error": f"Target must be at least bar weight ({bar_weight:g} kg).",
            "per_side": [],
            "achieved": bar_weight,
        }

    per_side_target = (target_weight - bar_weight) / 2
    if per_side_target < 0:
        per_side_target = 0

    # Round to nearest 1.25 kg (smallest standard plate)
    per_side_target = round(per_side_target / 1.25) * 1.25

    remaining = per_side_target
    per_side: list[float] = []
    for plate in sorted(available, reverse=True):
        while remaining >= plate - 0.001:
            per_side.append(plate)
            remaining = round(remaining - plate, 2)

    achieved = bar_weight + 2 * sum(per_side)
    return {
        "error": None,
        "per_side": per_side,
        "achieved": round(achieved, 2),
        "target": target_weight,
        "bar_weight": bar_weight,
    }
