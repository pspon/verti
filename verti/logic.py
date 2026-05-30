"""Pure horticulture helpers — no UI framework dependencies.

Shared by the Streamlit UI (via ``utils.helpers``) and the FastAPI UI (``web``).
"""

from __future__ import annotations

import math

import pandas as pd


# ─── Spacing & yield ──────────────────────────────────────────────────────────
def plants_per_sqft(spacing_in: float) -> float:
    """Square-foot gardening: plants per sq ft based on plant spacing (inches)."""
    if spacing_in <= 0:
        return 0
    return (12 / spacing_in) ** 2


def plants_in_bed(bed_width_ft: float, bed_length_ft: float, spacing_in: float) -> int:
    """Total plant count that fits in a rectangular bed."""
    return int(math.floor(plants_per_sqft(spacing_in) * bed_width_ft * bed_length_ft))


# ─── Companion / reference lookups ──────────────────────────────────────────────
def get_plant_color(plant_name: str, companion_data: dict) -> str:
    """Return a hex color for a plant, with fallback."""
    return companion_data.get("plant_colors", {}).get(plant_name, "#78909c")


def get_spacing(plant_name: str, companion_data: dict) -> dict:
    """Return spacing guide entry for a plant."""
    guide = companion_data.get("spacing_guide", {})
    return guide.get(plant_name, {"spacing_in": 12, "row_spacing_in": 18, "depth_in": 0.5})


def companion_relationship(plant_a: str, plant_b: str, companion_data: dict) -> str:
    """Return 'good', 'bad', or 'neutral' for two plants."""
    companions = companion_data.get("companions", {})
    info_a = companions.get(plant_a, {})
    if plant_b in info_a.get("good", []):
        return "good"
    if plant_b in info_a.get("bad", []):
        return "bad"
    info_b = companions.get(plant_b, {})
    if plant_a in info_b.get("good", []):
        return "good"
    if plant_a in info_b.get("bad", []):
        return "bad"
    return "neutral"


def calculate_planting_dates(plant_name: str, year: int, rules: dict) -> dict:
    """Calculate planting dates for a plant based on rules and year."""
    plant_rules = rules.get("planting_rules", {}).get(plant_name, {})
    if not plant_rules:
        return {"start_date": None, "end_date": None}

    # For the Toronto area, last frost is typically around May 9.
    last_frost_date = pd.Timestamp(year=year, month=5, day=9)
    start_date = end_date = None

    if plant_rules.get("start_indoors_delta"):
        start_date = last_frost_date + pd.Timedelta(days=plant_rules["start_indoors_delta"])
    elif plant_rules.get("last_frost_delta"):
        start_date = last_frost_date + pd.Timedelta(days=plant_rules["last_frost_delta"])

    if plant_rules.get("transplant_delta"):
        end_date = last_frost_date + pd.Timedelta(days=plant_rules["transplant_delta"])
    elif plant_rules.get("last_frost_delta"):
        end_date = last_frost_date + pd.Timedelta(days=plant_rules["last_frost_delta"])

    return {"start_date": start_date, "end_date": end_date}


# ─── Progress status helpers ────────────────────────────────────────────────────
STATUS_OPTIONS = ["not_started", "in_progress", "done", "skipped"]
STATUS_LABELS = {
    "not_started": "⬜ Not Started",
    "in_progress": "🔄 In Progress",
    "done": "✅ Done",
    "skipped": "⏭️ Skipped",
}
STATUS_COLORS = {
    "not_started": "#e0e0e0",
    "in_progress": "#fff9c4",
    "done": "#c8e6c9",
    "skipped": "#f3e5f5",
}


def get_plant_status(display_name: str, progress: dict) -> dict:
    """Return progress entry for a plant, with defaults."""
    default = {
        "start_status": "not_started",
        "transplant_status": "not_started",
        "start_actual": "",
        "transplant_actual": "",
        "notes": "",
        "bed": "",
    }
    return {**default, **progress.get(display_name, {})}


def bed_for_plant(seed_name: str, beds: list) -> str:
    """Find which bed a seed family is assigned to (first match)."""
    for bed in beds:
        if seed_name in bed.get("plants", []):
            return bed["name"]
    return ""
