"""
Shared utilities and helper functions for the Verti Garden Planner app.
"""

import math
from pathlib import Path

import pandas as pd
import streamlit as st

from verti import repository as repo
from verti.db import init_db

# Ensure the schema exists before any page reads/writes.
init_db()

# ─── Paths (kept for callers that still reference data files directly) ─────────
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"


# ─── Data Loading ─────────────────────────────────────────────────────────────
# These thin wrappers delegate to the UI-agnostic ``verti.repository`` (SQLite),
# preserving the historical signatures / return shapes so pages need no changes.
# The ``@st.cache_data`` layer is retained purely for in-session performance.
@st.cache_data(ttl=60)
def load_seeds_df(year: int = 2025) -> pd.DataFrame:
    """Load and pre-process the seeds for a specific year."""
    return repo.get_seeds_df(year)


def reload_seeds():
    """Clear the cache so the next load_seeds_df() call re-reads the DB."""
    load_seeds_df.clear()


@st.cache_data(ttl=300)
def load_companion_data() -> dict:
    """Load companion planting reference data."""
    return repo.get_companion_data()


@st.cache_data(ttl=60)
def load_planting_rules() -> dict:
    """Load planting rules."""
    return repo.get_planting_rules()


@st.cache_data(ttl=60)
def load_harvest_log() -> pd.DataFrame:
    """Load harvest log."""
    return repo.get_harvest_log()


def save_harvest_log(df: pd.DataFrame):
    """Persist harvest log."""
    repo.save_harvest_log(df)
    load_harvest_log.clear()


@st.cache_data(ttl=60)
def load_garden_beds() -> list:
    """Load saved garden bed layouts."""
    return repo.get_garden_beds()


def save_garden_beds(beds: list):
    """Persist garden bed layouts."""
    repo.save_garden_beds(beds)
    load_garden_beds.clear()


def save_planting_rules(rules: dict):
    """Persist planting rules."""
    repo.save_planting_rules(rules)
    load_planting_rules.clear()


# ─── Planting Progress ────────────────────────────────────────────────────────
# Progress structure per plant (keyed by Display Name):
# {
#   "Basil Genovese O Comune": {
#     "start_status": "done",       # not_started | in_progress | done | skipped
#     "transplant_status": "done",  # same options
#     "start_actual": "2025-03-05", # ISO date string or ""
#     "transplant_actual": "",
#     "notes": "free text",
#     "bed": "Raised Bed 1",        # assigned bed (overrides garden_beds.json if set)
#   }
# }

@st.cache_data(ttl=30)
def load_progress(year: int = 2025) -> dict:
    """Load planting progress for a specific year."""
    return repo.get_progress(year)


def save_progress(progress: dict, year: int = 2025):
    """Persist planting progress for a specific year."""
    repo.save_progress(progress, year)
    load_progress.clear()


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


# STATUS display helpers
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


# ─── Seeds persistence ─────────────────────────────────────────────────────────
def save_seeds_df(df: pd.DataFrame, year: int = 2025):
    """Save the seeds dataframe back to the database for a specific year."""
    repo.save_seeds_df(df, year)
    reload_seeds()


# ─── Spacing & Yield helpers ──────────────────────────────────────────────────
def plants_per_sqft(spacing_in: float) -> float:
    """Square-foot gardening: plants per sq ft based on plant spacing (inches)."""
    if spacing_in <= 0:
        return 0
    return (12 / spacing_in) ** 2


def plants_in_bed(bed_width_ft: float, bed_length_ft: float, spacing_in: float) -> int:
    """Total plant count that fits in a rectangular bed."""
    return int(math.floor(plants_per_sqft(spacing_in) * bed_width_ft * bed_length_ft))


def get_plant_color(plant_name: str, companion_data: dict) -> str:
    """Return a hex color for a plant, with fallback."""
    colors = companion_data.get("plant_colors", {})
    return colors.get(plant_name, "#78909c")


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

    # Get last frost date for the location (simplified - in a real app this would be configurable)
    # For Toronto area, last frost is typically around May 9
    last_frost_date = pd.Timestamp(year=year, month=5, day=9)

    start_date = None
    end_date = None

    # Calculate start date based on rules
    if plant_rules.get("start_indoors_delta"):
        start_date = last_frost_date + pd.Timedelta(days=plant_rules["start_indoors_delta"])
    elif plant_rules.get("last_frost_delta"):
        start_date = last_frost_date + pd.Timedelta(days=plant_rules["last_frost_delta"])

    # Calculate end date based on rules
    if plant_rules.get("transplant_delta"):
        end_date = last_frost_date + pd.Timedelta(days=plant_rules["transplant_delta"])
    elif plant_rules.get("last_frost_delta"):
        end_date = last_frost_date + pd.Timedelta(days=plant_rules["last_frost_delta"])

    return {"start_date": start_date, "end_date": end_date}


# ─── Page config helper ───────────────────────────────────────────────────────
def setup_page(title: str, icon: str = "🌱"):
    """Consistent page setup across all pages."""
    st.set_page_config(
        page_title=f"{title} | Verti Garden",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="auto",
    )
    # Mobile-friendly meta + custom CSS
    st.markdown(
        """
        <style>
        /* ── Mobile viewport meta ── */
        head::before {
            content: '';
        }
        /* ── Reduce padding on mobile ── */
        @media (max-width: 768px) {
            .block-container { padding: 0.5rem 0.75rem 1rem !important; }
            .stSidebar { display: none; }
            section[data-testid="stSidebar"] > div { padding-top: 1rem; }
        }
        /* ── Card-style metric boxes ── */
        div[data-testid="metric-container"] {
            background-color: #E8F5E9;
            border: 1px solid #C8E6C9;
            border-radius: 8px;
            padding: 12px;
        }
        /* ── Rounded buttons ── */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
        }
        /* ── Header branding ── */
        .verti-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 0.5rem;
        }
        /* ── Companion badge ── */
        .badge-good { background:#c8e6c9; color:#1b5e20; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
        .badge-bad  { background:#ffcdd2; color:#b71c1c; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
        .badge-neutral { background:#e0e0e0; color:#424242; padding:2px 8px; border-radius:12px; font-size:0.8rem; }
        /* ── Table tweaks ── */
        .dataframe th { background-color: #E8F5E9 !important; }
        /* ── Sidebar logo area ── */
        .sidebar-logo { text-align:center; padding: 1rem 0; font-size: 1.4rem; font-weight: 700; color: #2C3E2D; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav():
    """Render consistent sidebar navigation branding."""
    st.sidebar.markdown('<div class="sidebar-logo">🌿 Verti Garden</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
