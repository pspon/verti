"""
Shared utilities and helper functions for the Verti Garden Planner app.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from verti import repository as repo
from verti.db import init_db
# Pure horticulture helpers live in verti.logic (no Streamlit dependency);
# re-exported here so existing pages can keep importing them from utils.helpers.
from verti.logic import (  # noqa: F401
    STATUS_COLORS,
    STATUS_LABELS,
    STATUS_OPTIONS,
    bed_for_plant,
    calculate_planting_dates,
    companion_relationship,
    get_plant_color,
    get_plant_status,
    get_spacing,
    plants_in_bed,
    plants_per_sqft,
)

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


# ─── Seeds persistence ─────────────────────────────────────────────────────────
def save_seeds_df(df: pd.DataFrame, year: int = 2025):
    """Save the seeds dataframe back to the database for a specific year."""
    repo.save_seeds_df(df, year)
    reload_seeds()


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
