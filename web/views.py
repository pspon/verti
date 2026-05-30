"""View-model computation for the web UI.

Pure functions that turn the repository data into the dicts the templates
render. No FastAPI / Jinja imports here so the logic stays testable.
"""

from __future__ import annotations

import datetime

import pandas as pd

from verti import repository as repo
from verti.logic import (
    companion_relationship,
    get_plant_color,
    get_spacing,
    plants_in_bed,
    plants_per_sqft,
)

MONTHS = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
          7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
BED_TYPES = ["Raised Bed", "In-Ground", "Container", "Vertical"]
SUN_OPTIONS = ["Full Sun (6+ hrs)", "Part Sun (3-6 hrs)", "Shade (<3 hrs)"]
DEFAULT_PRICES = {
    "Tomato": 3.50, "Basil": 2.00, "Carrot": 1.50, "Lettuce": 2.50, "Radish": 1.80,
    "Cucumber": 1.80, "Beet": 2.00, "Spinach": 3.00, "Corn": 0.80, "Zucchini": 1.50,
    "Eggplant": 2.50, "Bokchoy": 2.00, "Snap Peas": 4.00, "Snow Peas": 4.00,
    "Ground Cherry": 6.00, "Parsnip": 2.50, "Green Onion": 2.00, "Parsley": 2.50,
    "Sage": 3.00, "Dill": 2.00, "Borage": 3.00, "Nasturtium": 2.50, "Shiso": 4.00,
}

SEASON_COLORS = {"Warm": "#FF9800", "Cool": "#42A5F5", "Perennial": "#66BB6A"}
METHOD_COLORS = {"Transplant": "#4CAF50", "Direct Sow": "#FF9800"}

NAV = [
    {"key": "dashboard", "label": "Dashboard", "icon": "🌿", "url": "/"},
    {"key": "schedule", "label": "Planting Schedule", "icon": "🗓️", "url": "/schedule"},
    {"key": "planner", "label": "Garden Planner", "icon": "🌱", "url": "/planner"},
    {"key": "database", "label": "Database Manager", "icon": "📊", "url": "/database"},
    {"key": "companions", "label": "Companion Plants", "icon": "🤝", "url": "/companions"},
    {"key": "analytics", "label": "Analytics", "icon": "📈", "url": "/analytics"},
]


def default_year() -> int:
    years = repo.available_years()
    return years[0] if years else datetime.date.today().year


def _bed_lookup(df: pd.DataFrame, beds: list, progress: dict) -> dict:
    """Map each plant Display Name to its assigned bed (progress overrides beds)."""
    lookup: dict[str, str] = {}
    for bed in beds:
        for fam in bed.get("plants", []):
            for dn in df[df["Seed"] == fam]["Display Name"].unique():
                lookup[dn] = bed["name"]
    for dn, pdata in progress.items():
        if pdata.get("bed"):
            lookup[dn] = pdata["bed"]
    return lookup


def dashboard_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    harvest = repo.get_harvest_log()
    today = datetime.date.today()

    def season_count(name: str) -> int:
        return int((df["Season"] == name).sum()) if "Season" in df.columns else 0

    metrics = {
        "total": len(df),
        "warm": season_count("Warm"),
        "cool": season_count("Cool"),
        "perennial": season_count("Perennial"),
    }

    # ── Tasks in the next 14 days (and recently overdue) ──
    upcoming = []
    for _, row in df.iterrows():
        name, method = row["Display Name"], row.get("Planting Method", "")
        for col, action, overdue in (
            ("Start Date", "Start Indoors / Sow", "Overdue — Start Indoors"),
            ("End Date", "Transplant / Direct Sow", "Overdue — Transplant"),
        ):
            d = row[col]
            if pd.notna(d):
                days = (d.date() - today).days
                if 0 <= days <= 14:
                    upcoming.append(
                        {"days": days, "action": action, "plant": name, "method": method}
                    )
                elif -3 <= days < 0:
                    upcoming.append(
                        {"days": days, "action": overdue, "plant": name,
                         "method": method, "overdue": True}
                    )
    upcoming.sort(key=lambda t: t["days"])
    for t in upcoming:
        d = t["days"]
        t["label"] = (
            "Today" if d == 0 else (f"In {d} days" if d > 0 else f"{abs(d)} days ago")
        )

    season_counts = (
        df["Season"].value_counts().to_dict() if "Season" in df.columns else {}
    )
    method_counts = (
        df["Planting Method"].value_counts().to_dict() if "Planting Method" in df.columns else {}
    )
    brand_counts = []
    if "Brand" in df.columns and len(df):
        for brand, cnt in df["Brand"].value_counts().head(6).items():
            brand_counts.append(
                {"brand": brand, "count": int(cnt), "pct": int(cnt / len(df) * 100)}
            )

    return {
        "year": year,
        "metrics": metrics,
        "upcoming": upcoming,
        "season_counts": season_counts,
        "method_counts": method_counts,
        "brand_counts": brand_counts,
        "harvest_count": len(harvest),
        "timeline_df": _timeline_window(df, today),
    }


def _timeline_window(df: pd.DataFrame, today: datetime.date) -> pd.DataFrame:
    window_start = pd.Timestamp(today)
    window_end = pd.Timestamp(today + datetime.timedelta(weeks=6))
    mask = (
        ((df["Start Date"] <= window_end) & (df["End Date"] >= window_start))
        | ((df["Start Date"] >= window_start) & (df["Start Date"] <= window_end))
    )
    return df[mask].copy()


def schedule_context(year: int, seasons: list[str] | None = None,
                     methods: list[str] | None = None,
                     beds_filter: list[str] | None = None) -> dict:
    df = repo.get_seeds_df(year)
    beds = repo.get_garden_beds()
    progress = repo.get_progress(year)
    today = datetime.date.today()

    lookup = _bed_lookup(df, beds, progress)
    df["Bed"] = df["Display Name"].map(lookup).fillna("Unassigned")

    all_seasons = sorted(df["Season"].dropna().unique()) if "Season" in df.columns else []
    all_methods = (
        sorted(df["Planting Method"].dropna().unique())
        if "Planting Method" in df.columns else []
    )
    all_beds = sorted({b["name"] for b in beds}) + ["Unassigned"]

    if seasons:
        df = df[df["Season"].isin(seasons)]
    if methods:
        df = df[df["Planting Method"].isin(methods)]
    if beds_filter:
        df = df[df["Bed"].isin(beds_filter)]

    df = df.sort_values("Start Date")

    rows = []
    for _, r in df.iterrows():
        dn = r["Display Name"]
        st_status = progress.get(dn, {}).get("start_status", "not_started")
        tp_status = progress.get(dn, {}).get("transplant_status", "not_started")
        rows.append({
            "plant": dn,
            "bed": r["Bed"],
            "season": r.get("Season", ""),
            "method": r.get("Planting Method", ""),
            "start": r["Start Date"].date() if pd.notna(r["Start Date"]) else None,
            "end": r["End Date"].date() if pd.notna(r["End Date"]) else None,
            "start_status": st_status,
            "transplant_status": tp_status,
        })

    done = sum(1 for x in rows if x["transplant_status"] == "done")
    return {
        "year": year,
        "rows": rows,
        "today": today,
        "all_seasons": all_seasons,
        "all_methods": all_methods,
        "all_beds": all_beds,
        "sel_seasons": seasons or all_seasons,
        "sel_methods": methods or all_methods,
        "sel_beds": beds_filter or all_beds,
        "total": len(rows),
        "done": done,
        "timeline_df": df,
        "years": repo.available_years(),
    }


# ─── Garden Planner ───────────────────────────────────────────────────────────
def planner_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    beds = repo.get_garden_beds()
    families = sorted(df["Seed"].unique())

    bed_views = []
    for bed in beds:
        plants = bed.get("plants", [])
        good, bad = [], []
        for i, p1 in enumerate(plants):
            for p2 in plants[i + 1:]:
                rel = companion_relationship(p1, p2, companion)
                if rel == "good":
                    good.append(f"{p1} & {p2}")
                elif rel == "bad":
                    bad.append(f"{p1} & {p2}")
        bed_views.append({
            **bed,
            "area": round(bed["width"] * bed["length"]),
            "good": good,
            "bad": bad,
        })

    return {
        "year": year, "years": repo.available_years(), "beds": beds, "bed_views": bed_views,
        "companion": companion, "families": families,
        "bed_types": BED_TYPES, "sun_options": SUN_OPTIONS,
    }


def spacing_context(year: int, plant: str | None, width: float, length: float) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    families = sorted(df["Seed"].unique())
    plant = plant or (families[0] if families else "")

    info = get_spacing(plant, companion)
    sqft = width * length
    count = plants_in_bed(width, length, info["spacing_in"])

    per_sq_csv = ""
    rows = df[df["Seed"] == plant]
    if not rows.empty and "Per Square" in rows.columns:
        ps = rows["Per Square"].dropna()
        if not ps.empty:
            per_sq_csv = ps.iloc[0]
    sfg_count = int(per_sq_csv * sqft) if per_sq_csv not in ("", None) else None

    reference = []
    for p, g in companion.get("spacing_guide", {}).items():
        pr = df[df["Seed"] == p]
        csv_ps = ""
        if not pr.empty and "Per Square" in pr.columns:
            psv = pr["Per Square"].dropna()
            if not psv.empty:
                csv_ps = psv.iloc[0]
        reference.append({
            "plant": p, "spacing": g["spacing_in"], "row": g["row_spacing_in"],
            "depth": g["depth_in"], "sfg": round(plants_per_sqft(g["spacing_in"]), 1),
            "csv": csv_ps,
        })
    reference.sort(key=lambda r: r["plant"])

    return {
        "year": year, "years": repo.available_years(), "families": families, "plant": plant,
        "width": width, "length": length, "info": info, "sqft": round(sqft),
        "count": count, "per_sq_csv": per_sq_csv, "sfg_count": sfg_count, "reference": reference,
    }


def sunlight_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    sun_icons = companion.get("sun_icons", {})

    groups = []
    if "Sun" in df.columns:
        for sun_level, plants in sorted(df.groupby("Sun")["Display Name"].apply(list).items()):
            families: dict[str, list[str]] = {}
            for p in plants:
                families.setdefault(p.split(" ")[0], []).append(p)
            groups.append({
                "level": sun_level, "icon": sun_icons.get(sun_level, "🌿"), "count": len(plants),
                "families": [
                    {"seed": s, "color": get_plant_color(s, companion), "variants": v}
                    for s, v in sorted(families.items())
                ],
            })
    sun_counts = df["Sun"].value_counts().to_dict() if "Sun" in df.columns else {}
    return {"year": year, "years": repo.available_years(), "groups": groups,
            "sun_counts": sun_counts}


# ─── Database Manager ───────────────────────────────────────────────────────────
def seed_display(s: dict) -> dict:
    """Map a raw seed dict (from the repository) to the table-row view shape."""
    return {
        "id": s["id"],
        "name": s["display_name"] or s["seed"],
        "brand": s.get("brand", ""),
        "season": s.get("season", ""),
        "sun": s.get("sun", ""),
        "frost": s.get("frost", ""),
        "method": s.get("planting_method", ""),
        "days": "" if s.get("days_to_maturity") is None else s["days_to_maturity"],
        "per_square": "" if s.get("per_square") is None else s["per_square"],
        "start": s.get("start_indoors"),
        "end": s.get("transplant_sow"),
        "plant_this_year": bool(s.get("plant_this_year")),
    }


def _seed_edit_options(seeds: list[dict]) -> dict:
    """Distinct existing values, offered as datalist suggestions in the editor."""
    def distinct(key: str) -> list[str]:
        return sorted({(s.get(key) or "").strip() for s in seeds if (s.get(key) or "").strip()})
    return {
        "seasons": distinct("season"),
        "methods": distinct("planting_method"),
        "suns": distinct("sun"),
        "frosts": distinct("frost"),
        "brands": distinct("brand"),
    }


def database_context(year: int, search: str = "", season: str = "All",
                     method: str = "All", frost: str = "All") -> dict:
    seeds = repo.list_seeds(year)

    def options(key: str) -> list[str]:
        values = {(s.get(key) or "").strip() for s in seeds if (s.get(key) or "").strip()}
        return ["All"] + sorted(values)

    opts = {"seasons": options("season"), "methods": options("planting_method"),
            "frosts": options("frost")}

    s_lower = search.strip().lower()
    filtered = []
    for s in seeds:
        if s_lower and not any(
            s_lower in (s.get(k) or "").lower() for k in ("seed", "variant", "brand")
        ):
            continue
        if season != "All" and s.get("season") != season:
            continue
        if method != "All" and s.get("planting_method") != method:
            continue
        if frost != "All" and s.get("frost") != frost:
            continue
        filtered.append(s)

    return {
        "year": year, "years": repo.available_years(), "options": opts,
        "records": [seed_display(s) for s in filtered],
        "edit_options": _seed_edit_options(seeds),
        "count": len(filtered), "search": search,
        "sel_season": season, "sel_method": method, "sel_frost": frost,
    }


# ─── Companion Plants ─────────────────────────────────────────────────────────
def _all_plants(df: pd.DataFrame, companions: dict) -> list[str]:
    return sorted(set(list(companions.keys()) + list(df["Seed"].unique())))


def companion_lookup_context(year: int, plant: str | None,
                             plant_a: str | None, plant_b: str | None) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    companions = companion.get("companions", {})
    plants = _all_plants(df, companions)
    plant = plant or (plants[0] if plants else "")

    info = companions.get(plant, {})
    good = [{"name": p, "color": get_plant_color(p, companion)} for p in info.get("good", [])]
    bad = info.get("bad", [])

    pair = None
    if plant_a and plant_b:
        rel = companion_relationship(plant_a, plant_b, companion)
        note = companions.get(plant_a, {}).get("notes", "")
        pair = {"a": plant_a, "b": plant_b, "rel": rel, "note": note}

    return {
        "year": year, "years": repo.available_years(), "plants": plants, "plant": plant,
        "color": get_plant_color(plant, companion), "notes": info.get("notes", ""),
        "good": good, "bad": bad, "pair": pair,
        "plant_a": plant_a or plant, "plant_b": plant_b,
    }


def companion_matrix_context(year: int, selected: list[str] | None) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    companions = companion.get("companions", {})
    plants = _all_plants(df, companions)
    if not selected:
        selected = [p for p in sorted(companions.keys())[:16] if p in plants]

    z, hover = [], []
    good_count = bad_count = 0
    for p1 in selected:
        row_z, row_h = [], []
        for p2 in selected:
            if p1 == p2:
                row_z.append(0)
                row_h.append(f"{p1} (same plant)")
            else:
                rel = companion_relationship(p1, p2, companion)
                if rel == "good":
                    row_z.append(1)
                    row_h.append(f"✅ {p1} + {p2}: Good")
                    good_count += 1
                elif rel == "bad":
                    row_z.append(-1)
                    row_h.append(f"⛔ {p1} + {p2}: Poor")
                    bad_count += 1
                else:
                    row_z.append(0)
                    row_h.append(f"⬜ {p1} + {p2}: Neutral")
        z.append(row_z)
        hover.append(row_h)

    return {
        "year": year, "years": repo.available_years(), "plants": plants, "selected": selected,
        "z": z, "labels": selected, "hover": hover,
        "good_count": good_count // 2, "bad_count": bad_count // 2,
    }


def companion_stats_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    companions = companion.get("companions", {})
    stats = []
    for plant in sorted(df["Seed"].unique()):
        info = companions.get(plant, {})
        stats.append({
            "plant": plant, "in_db": plant in companions,
            "good": len(info.get("good", [])), "bad": len(info.get("bad", [])),
            "notes": info.get("notes", ""),
        })
    stats.sort(key=lambda r: r["good"], reverse=True)
    return {"stats": stats}


# ─── Analytics ─────────────────────────────────────────────────────────────────
def analytics_harvest_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    harvests = repo.list_harvests()
    companion = repo.get_companion_data()
    families = sorted(df["Seed"].unique())
    variants = sorted(df["Display Name"].unique())

    hdf = repo.get_harvest_log()
    total_kg = float(hdf["Quantity_kg"].sum()) if not hdf.empty else 0.0
    plant_totals = pd.DataFrame(columns=["Plant", "Total (kg)"])
    daily = pd.DataFrame(columns=["Date", "Plant", "Quantity_kg"])
    if not hdf.empty:
        plant_totals = (hdf.groupby("Plant")["Quantity_kg"].sum()
                        .sort_values(ascending=False).reset_index())
        plant_totals.columns = ["Plant", "Total (kg)"]
        daily = hdf.groupby(["Date", "Plant"])["Quantity_kg"].sum().reset_index()

    return {
        "year": year, "years": repo.available_years(), "companion": companion,
        "families": families, "variants": variants, "harvests": harvests,
        "today": datetime.date.today(),
        "total_kg": total_kg, "entries": len(harvests),
        "unique_plants": hdf["Plant"].nunique() if not hdf.empty else 0,
        "plant_totals": plant_totals, "daily": daily,
        "has_data": not hdf.empty,
        "variant_map": {f: sorted(df[df["Seed"] == f]["Display Name"].unique()) for f in families},
    }


def analytics_insights_context(year: int) -> dict:
    df = repo.get_seeds_df(year)
    activity = df.copy()
    activity["Start Month"] = activity["Start Date"].dt.month
    activity["End Month"] = activity["End Date"].dt.month

    starts = activity["Start Month"].dropna().astype(int).value_counts().sort_index()
    ends = activity["End Month"].dropna().astype(int).value_counts().sort_index()
    months = sorted(set(starts.index) | set(ends.index))
    merged = pd.DataFrame({
        "Month": months,
        "Month Label": [MONTHS[m] for m in months],
        "Starts": [int(starts.get(m, 0)) for m in months],
        "Transplants": [int(ends.get(m, 0)) for m in months],
    })

    days_numeric = pd.to_numeric(df["Days"], errors="coerce").dropna()
    day_stats = None
    if not days_numeric.empty:
        day_stats = {"min": int(days_numeric.min()), "avg": int(days_numeric.mean()),
                     "max": int(days_numeric.max())}

    frost_counts = df["Frost"].value_counts().to_dict() if "Frost" in df.columns else {}
    return {
        "year": year, "years": repo.available_years(), "merged": merged,
        "days_numeric": days_numeric, "day_stats": day_stats, "frost_counts": frost_counts,
    }


def analytics_cost_context(year: int, prices: dict | None, seed_cost: float,
                           supplies_cost: float) -> dict:
    df = repo.get_seeds_df(year)
    companion = repo.get_companion_data()
    families = sorted(df["Seed"].unique())
    prices = prices or {p: DEFAULT_PRICES.get(p, 2.00) for p in families}
    investment = seed_cost + supplies_cost

    hdf = repo.get_harvest_log()
    result = {
        "year": year, "years": repo.available_years(), "companion": companion,
        "families": families, "prices": prices, "seed_cost": seed_cost,
        "supplies_cost": supplies_cost, "investment": investment, "has_data": not hdf.empty,
    }
    if hdf.empty:
        return result

    by_plant = hdf.groupby("Plant")["Quantity_kg"].sum().reset_index()
    by_plant.columns = ["Plant", "Harvested (kg)"]
    by_plant["Market Price ($/kg)"] = by_plant["Plant"].map(lambda p: prices.get(p, 2.0))
    by_plant["Value ($)"] = (by_plant["Harvested (kg)"] * by_plant["Market Price ($/kg)"]).round(2)
    total_value = float(by_plant["Value ($)"].sum())
    roi = total_value - investment
    result.update({
        "cost_df": by_plant, "total_value": total_value, "roi": roi,
        "roi_pct": (roi / investment * 100) if investment > 0 else 0,
        "total_harvested": float(hdf["Quantity_kg"].sum()),
    })
    return result
