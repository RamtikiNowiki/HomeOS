"""Weight units — app stores and displays pounds (US)."""

KG_TO_LB = 2.2046226218
LB_TO_KG = 1.0 / KG_TO_LB

DEFAULT_BAR_LB = 45.0
DEFAULT_PLATES_LB = (45, 35, 25, 10, 5, 2.5)
SMALLEST_PLATE_LB = 2.5


def format_weight(value) -> str:
    """Format a weight number for display (no unit suffix)."""
    if value is None:
        return "—"
    return f"{value:g}"


def format_num(value) -> str:
    """Format a generic number (RPE, body fat %, etc.)."""
    if value is None:
        return "—"
    return f"{value:g}"
