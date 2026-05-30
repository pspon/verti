"""UI-agnostic data access for the Verti Garden Planner.

Everything that touches the database lives here. Functions return plain Python
structures (dicts / lists) or pandas DataFrames that mirror the shapes the app
historically read from flat files, so callers don't need to know about the ORM.

This module is deliberately free of any Streamlit / web-framework imports so it
can be reused by the Streamlit UI today and the FastAPI UI next.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from sqlmodel import select

from verti.db import get_session, init_db
from verti.models import (
    BedPlant,
    Companion,
    GardenBed,
    Harvest,
    IconMap,
    PlantColor,
    PlantingProgress,
    PlantingRule,
    Seed,
    SpacingGuide,
)

# Column layout the rest of the app expects from the seeds frame.
SEED_COLUMNS = [
    "Seed", "Variant", "Brand", "Year", "Days", "Days (after transplant)",
    "Season", "Per Square", "Sun", "Frost", "Planting Method", "Plant in 2025",
    "Transplant Delta", "Last Frost Delta", "Start Date", "End Date", "Display Name",
]
HARVEST_COLUMNS = ["Date", "Plant", "Variant", "Quantity_kg", "Notes"]


def _to_date(value) -> Optional[date]:
    """Coerce a value to a python ``date`` or ``None``."""
    ts = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(ts) else ts.date()


# ─── Seeds ────────────────────────────────────────────────────────────────────
def get_seeds_df(year: int = 2025) -> pd.DataFrame:
    """Return the seeds for ``year`` as a DataFrame matching the legacy layout.

    Falls back to the earliest available year if the requested one is empty,
    preserving the previous file-based fallback behaviour.
    """
    with get_session() as s:
        rows = s.exec(select(Seed).where(Seed.season_year == year)).all()
        if not rows:
            years = sorted(set(s.exec(select(Seed.season_year)).all()))
            if years:
                rows = s.exec(select(Seed).where(Seed.season_year == years[0])).all()

    records = []
    for r in rows:
        records.append({
            "Seed": str(r.seed),
            "Variant": str(r.variant),
            "Brand": r.brand,
            "Year": r.packet_year,
            "Days": r.days_to_maturity,
            "Days (after transplant)": r.days_after_transplant,
            "Season": r.season,
            "Per Square": r.per_square,
            "Sun": r.sun,
            "Frost": r.frost,
            "Planting Method": r.planting_method,
            "Plant in 2025": r.plant_this_year,
            "Transplant Delta": r.transplant_delta,
            "Last Frost Delta": r.last_frost_delta,
            "Start Date": r.start_indoors,
            "End Date": r.transplant_sow,
            "Display Name": r.display_name,
        })

    df = pd.DataFrame(records, columns=SEED_COLUMNS)
    df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
    df["End Date"] = pd.to_datetime(df["End Date"], errors="coerce")
    # Direct Sow: start date is 3 days before sow date (legacy rule).
    idx = df["Planting Method"] == "Direct Sow"
    df.loc[idx, "Start Date"] = df.loc[idx, "End Date"] - pd.Timedelta(days=3)
    return df


def save_seeds_df(df: pd.DataFrame, year: int = 2025) -> None:
    """Replace the seed set for ``year`` with the contents of ``df``."""
    init_db()
    with get_session() as s:
        for existing in s.exec(select(Seed).where(Seed.season_year == year)).all():
            s.delete(existing)
        s.commit()
        for _, row in df.iterrows():
            s.add(_seed_from_row(row, year))
        s.commit()


def _seed_from_row(row: pd.Series, year: int) -> Seed:
    def num(key, cast):
        val = row.get(key)
        if pd.isna(val) or val == "":
            return None
        try:
            return cast(val)
        except (ValueError, TypeError):
            return None

    return Seed(
        season_year=year,
        seed=str(row.get("Seed", "") or ""),
        variant=str(row.get("Variant", "") or "").replace("nan", ""),
        brand=str(row.get("Brand", "") or ""),
        packet_year=num("Year", int),
        days_to_maturity=num("Days", int),
        days_after_transplant=num("Days (after transplant)", int),
        season=str(row.get("Season", "") or ""),
        per_square=num("Per Square", float),
        sun=str(row.get("Sun", "") or ""),
        frost=str(row.get("Frost", "") or ""),
        planting_method=str(row.get("Planting Method", "") or ""),
        plant_this_year=_to_bool(row.get("Plant in 2025")),
        transplant_delta=num("Transplant Delta", int),
        last_frost_delta=num("Last Frost Delta", int),
        start_indoors=_to_date(
            row.get("Start Date") if "Start Date" in row else row.get("Start Indoors")
        ),
        transplant_sow=_to_date(
            row.get("End Date") if "End Date" in row else row.get("Transplant / Sow")
        ),
    )


def _to_bool(value) -> Optional[bool]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        v = value.strip().upper()
        if v in ("TRUE", "1", "YES"):
            return True
        if v in ("FALSE", "0", "NO", ""):
            return False if v else None
    return bool(value)


# ─── Companion / reference data ───────────────────────────────────────────────
def get_companion_data() -> dict:
    """Reconstruct the legacy companion JSON shape from reference tables."""
    with get_session() as s:
        companions = {
            c.plant: {"good": c.good or [], "bad": c.bad or [], "notes": c.notes}
            for c in s.exec(select(Companion)).all()
        }
        spacing_guide = {
            g.plant: {
                "spacing_in": g.spacing_in,
                "row_spacing_in": g.row_spacing_in,
                "depth_in": g.depth_in,
            }
            for g in s.exec(select(SpacingGuide)).all()
        }
        plant_colors = {c.plant: c.color for c in s.exec(select(PlantColor)).all()}
        sun_icons, frost_icons = {}, {}
        for i in s.exec(select(IconMap)).all():
            (sun_icons if i.category == "sun" else frost_icons)[i.key] = i.icon

    return {
        "companions": companions,
        "spacing_guide": spacing_guide,
        "plant_colors": plant_colors,
        "sun_icons": sun_icons,
        "frost_icons": frost_icons,
    }


# ─── Planting rules ───────────────────────────────────────────────────────────
def get_planting_rules() -> dict:
    """Return the legacy ``{"planting_rules": {display_name: {...}}}`` shape."""
    with get_session() as s:
        rules = {}
        for r in s.exec(select(PlantingRule)).all():
            rules[r.display_name] = {
                "seed": r.seed,
                "variant": r.variant,
                "brand": r.brand,
                "days_to_maturity": r.days_to_maturity,
                "days_after_transplant": r.days_after_transplant,
                "season": r.season,
                "per_square": r.per_square,
                "sun": r.sun,
                "frost_tolerance": r.frost_tolerance,
                "planting_method": r.planting_method,
                "start_indoors_delta": r.start_indoors_delta,
                "transplant_delta": r.transplant_delta,
                "last_frost_delta": r.last_frost_delta,
            }
    return {"planting_rules": rules}


def save_planting_rules(rules: dict) -> None:
    init_db()
    data = rules.get("planting_rules", {})
    with get_session() as s:
        for existing in s.exec(select(PlantingRule)).all():
            s.delete(existing)
        s.commit()
        for name, r in data.items():
            s.add(PlantingRule(
                display_name=name,
                seed=r.get("seed", ""),
                variant=r.get("variant", ""),
                brand=r.get("brand", ""),
                days_to_maturity=r.get("days_to_maturity"),
                days_after_transplant=r.get("days_after_transplant"),
                season=r.get("season", ""),
                per_square=r.get("per_square"),
                sun=r.get("sun", ""),
                frost_tolerance=r.get("frost_tolerance", ""),
                planting_method=r.get("planting_method", ""),
                start_indoors_delta=r.get("start_indoors_delta"),
                transplant_delta=r.get("transplant_delta"),
                last_frost_delta=r.get("last_frost_delta"),
            ))
        s.commit()


# ─── Harvest log ──────────────────────────────────────────────────────────────
def get_harvest_log() -> pd.DataFrame:
    with get_session() as s:
        rows = s.exec(select(Harvest)).all()
    records = [
        {"Date": r.date, "Plant": r.plant, "Variant": r.variant,
         "Quantity_kg": r.quantity_kg, "Notes": r.notes}
        for r in rows
    ]
    df = pd.DataFrame(records, columns=HARVEST_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def save_harvest_log(df: pd.DataFrame) -> None:
    init_db()
    with get_session() as s:
        for existing in s.exec(select(Harvest)).all():
            s.delete(existing)
        s.commit()
        for _, row in df.iterrows():
            s.add(Harvest(
                date=_to_date(row.get("Date")),
                plant=str(row.get("Plant", "") or ""),
                variant=str(row.get("Variant", "") or ""),
                quantity_kg=(None if pd.isna(row.get("Quantity_kg"))
                             else float(row.get("Quantity_kg"))),
                notes=str(row.get("Notes", "") or ""),
            ))
        s.commit()


# ─── Garden beds ──────────────────────────────────────────────────────────────
def get_garden_beds() -> list:
    """Return beds as a list of dicts matching the legacy JSON shape."""
    with get_session() as s:
        beds = s.exec(select(GardenBed)).all()
        return [
            {
                "name": b.name,
                "width": b.width,
                "length": b.length,
                "type": b.bed_type,
                "sun": b.sun,
                "plants": [p.plant_name for p in b.plants],
            }
            for b in beds
        ]


def save_garden_beds(beds: list) -> None:
    init_db()
    with get_session() as s:
        for existing in s.exec(select(GardenBed)).all():
            s.delete(existing)
        s.commit()
        for b in beds:
            bed = GardenBed(
                name=b.get("name", ""),
                width=float(b.get("width", 0) or 0),
                length=float(b.get("length", 0) or 0),
                bed_type=b.get("type", ""),
                sun=b.get("sun", ""),
            )
            bed.plants = [
                BedPlant(plant_name=name, position=i)
                for i, name in enumerate(b.get("plants", []))
            ]
            s.add(bed)
        s.commit()


# ─── Planting progress ────────────────────────────────────────────────────────
def get_progress(year: int = 2025) -> dict:
    """Return progress keyed by display name, matching the legacy JSON shape."""
    with get_session() as s:
        rows = s.exec(select(PlantingProgress).where(PlantingProgress.season_year == year)).all()
        return {
            r.display_name: {
                "start_status": r.start_status,
                "transplant_status": r.transplant_status,
                "start_actual": r.start_actual.isoformat() if r.start_actual else "",
                "transplant_actual": r.transplant_actual.isoformat() if r.transplant_actual else "",
                "notes": r.notes,
                "bed": r.bed,
            }
            for r in rows
        }


def save_progress(progress: dict, year: int = 2025) -> None:
    init_db()
    with get_session() as s:
        for existing in s.exec(
            select(PlantingProgress).where(PlantingProgress.season_year == year)
        ).all():
            s.delete(existing)
        s.commit()
        for name, p in progress.items():
            s.add(PlantingProgress(
                season_year=year,
                display_name=name,
                start_status=p.get("start_status", "not_started"),
                transplant_status=p.get("transplant_status", "not_started"),
                start_actual=_to_date(p.get("start_actual")),
                transplant_actual=_to_date(p.get("transplant_actual")),
                notes=p.get("notes", ""),
                bed=p.get("bed", ""),
            ))
        s.commit()


def available_years() -> list[int]:
    """Distinct plan years present in the seed table (descending)."""
    with get_session() as s:
        return sorted(set(s.exec(select(Seed.season_year)).all()), reverse=True)
