"""View-model computation for the web UI.

Pure functions that turn the repository data into the dicts the templates
render. No FastAPI / Jinja imports here so the logic stays testable.
"""

from __future__ import annotations

import datetime

import pandas as pd

from verti import repository as repo

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
