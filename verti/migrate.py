"""One-off migration: import the legacy flat files (CSV/JSON) into SQLite.

Run with::

    python -m verti.migrate          # import only if the DB looks empty
    python -m verti.migrate --force  # wipe and re-import from the flat files

After migration the SQLite database is the source of truth; the original files
are kept as a backup but are no longer read by the app.
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd
from sqlmodel import select

from verti.db import ROOT_DIR, get_session, init_db
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

DATA_DIR = ROOT_DIR / "data"
SEEDS_DIR = DATA_DIR / "seeds"
PROGRESS_DIR = DATA_DIR / "progress"
HARVEST_DIR = DATA_DIR / "harvests"


def _date(value):
    ts = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def _num(value, cast):
    if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return cast(value)
    except (ValueError, TypeError):
        return None


def _bool(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value).strip().upper() in ("TRUE", "1", "YES")


def import_seeds(session) -> int:
    count = 0
    for csv_path in sorted(SEEDS_DIR.glob("*-seeds.csv")):
        year = int(csv_path.stem.split("-")[0])
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            session.add(Seed(
                season_year=year,
                seed=str(row.get("Seed", "") or ""),
                variant="" if pd.isna(row.get("Variant")) else str(row.get("Variant")),
                brand="" if pd.isna(row.get("Brand")) else str(row.get("Brand")),
                packet_year=_num(row.get("Year"), int),
                days_to_maturity=_num(row.get("Days"), int),
                days_after_transplant=_num(row.get("Days (after transplant)"), int),
                season="" if pd.isna(row.get("Season")) else str(row.get("Season")),
                per_square=_num(row.get("Per Square"), float),
                sun="" if pd.isna(row.get("Sun")) else str(row.get("Sun")),
                frost="" if pd.isna(row.get("Frost")) else str(row.get("Frost")),
                planting_method=("" if pd.isna(row.get("Planting Method"))
                                 else str(row.get("Planting Method"))),
                plant_this_year=_bool(row.get("Plant in 2025")),
                transplant_delta=_num(row.get("Transplant Delta"), int),
                last_frost_delta=_num(row.get("Last Frost Delta"), int),
                start_indoors=_date(row.get("Start Indoors")),
                transplant_sow=_date(row.get("Transplant / Sow")),
            ))
            count += 1
    return count


def import_companions(session) -> int:
    path = DATA_DIR / "companion_plants.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for plant, info in data.get("companions", {}).items():
        session.add(Companion(
            plant=plant,
            good=info.get("good", []),
            bad=info.get("bad", []),
            notes=info.get("notes", ""),
        ))
        count += 1
    for plant, g in data.get("spacing_guide", {}).items():
        session.add(SpacingGuide(
            plant=plant,
            spacing_in=g.get("spacing_in"),
            row_spacing_in=g.get("row_spacing_in"),
            depth_in=g.get("depth_in"),
        ))
    for plant, color in data.get("plant_colors", {}).items():
        session.add(PlantColor(plant=plant, color=color))
    for key, icon in data.get("sun_icons", {}).items():
        session.add(IconMap(category="sun", key=key, icon=icon))
    for key, icon in data.get("frost_icons", {}).items():
        session.add(IconMap(category="frost", key=key, icon=icon))
    return count


def import_rules(session) -> int:
    path = DATA_DIR / "planting_rules.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8")).get("planting_rules", {})
    for name, r in data.items():
        session.add(PlantingRule(
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
    return len(data)


def import_beds(session) -> int:
    path = DATA_DIR / "garden_beds.json"
    if not path.exists():
        return 0
    beds = json.loads(path.read_text(encoding="utf-8"))
    for b in beds:
        bed = GardenBed(
            name=b.get("name", ""),
            width=float(b.get("width", 0) or 0),
            length=float(b.get("length", 0) or 0),
            bed_type=b.get("type", ""),
            sun=b.get("sun", ""),
        )
        bed.plants = [BedPlant(plant_name=n, position=i) for i, n in enumerate(b.get("plants", []))]
        session.add(bed)
    return len(beds)


def import_progress(session) -> int:
    count = 0
    if not PROGRESS_DIR.exists():
        return 0
    for path in sorted(PROGRESS_DIR.glob("*_progress.json")):
        year = int(path.stem.split("_")[0])
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, p in data.items():
            session.add(PlantingProgress(
                season_year=year,
                display_name=name,
                start_status=p.get("start_status", "not_started"),
                transplant_status=p.get("transplant_status", "not_started"),
                start_actual=_date(p.get("start_actual")),
                transplant_actual=_date(p.get("transplant_actual")),
                notes=p.get("notes", ""),
                bed=p.get("bed", ""),
            ))
            count += 1
    return count


def _harvest_year(path, fallback: int) -> int:
    """Derive the plan year from a harvest filename (``2025_harvest.csv`` → 2025)."""
    prefix = path.stem.split("_")[0]
    return int(prefix) if prefix.isdigit() else fallback


def import_harvests(session) -> int:
    count = 0
    fallback_year = min(
        (int(p.stem.split("-")[0]) for p in SEEDS_DIR.glob("*-seeds.csv")),
        default=pd.Timestamp.now().year,
    )
    candidates = [DATA_DIR / "harvest_log.csv"]
    if HARVEST_DIR.exists():
        candidates += sorted(HARVEST_DIR.glob("*.csv"))
    for path in candidates:
        if not path.exists():
            continue
        year = _harvest_year(path, fallback_year)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            session.add(Harvest(
                season_year=year,
                date=_date(row.get("Date")),
                plant=str(row.get("Plant", "") or ""),
                variant="" if pd.isna(row.get("Variant")) else str(row.get("Variant")),
                quantity_kg=_num(row.get("Quantity_kg"), float),
                notes="" if pd.isna(row.get("Notes")) else str(row.get("Notes")),
            ))
            count += 1
    return count


def db_has_data(session) -> bool:
    return session.exec(select(Seed)).first() is not None


def run(force: bool = False) -> None:
    init_db()
    with get_session() as session:
        if db_has_data(session) and not force:
            print("Database already contains data; nothing to do. Use --force to re-import.")
            return
        if force:
            for model in (Seed, Companion, SpacingGuide, PlantColor, IconMap,
                          PlantingRule, BedPlant, GardenBed, PlantingProgress, Harvest):
                for obj in session.exec(select(model)).all():
                    session.delete(obj)
            session.commit()

        summary = {
            "seeds": import_seeds(session),
            "companions": import_companions(session),
            "planting_rules": import_rules(session),
            "garden_beds": import_beds(session),
            "progress": import_progress(session),
            "harvests": import_harvests(session),
        }
        session.commit()

    print("Migration complete:")
    for key, value in summary.items():
        print(f"  {key:>15}: {value}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import legacy flat files into SQLite.")
    parser.add_argument("--force", action="store_true", help="Wipe existing DB rows and re-import.")
    args = parser.parse_args(argv)
    run(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
