"""FastAPI application entry point for the Verti Garden Planner web UI."""

from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from verti import repository as repo
from verti.db import init_db
from web import charts, views

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Verti Garden Planner")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals["nav"] = views.NAV


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _page(request: Request, template: str, active: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(
        request, template, {"active": active, **ctx}
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, year: int | None = None):
    year = year or views.default_year()
    ctx = views.dashboard_context(year)
    ctx["timeline_html"] = charts.timeline(ctx["timeline_df"], datetime.date.today())
    ctx["donut_html"] = charts.season_donut(ctx["season_counts"], include_js=False)
    ctx["method_html"] = charts.method_bar(ctx["method_counts"], include_js=False)
    ctx["years"] = repo.available_years()
    return _page(request, "dashboard.html", "dashboard", **ctx)


@app.get("/schedule", response_class=HTMLResponse)
def schedule(
    request: Request,
    year: int | None = None,
    season: list[str] | None = Query(default=None),
    method: list[str] | None = Query(default=None),
    bed: list[str] | None = Query(default=None),
):
    year = year or views.default_year()
    ctx = views.schedule_context(year, seasons=season, methods=method, beds_filter=bed)
    ctx["timeline_html"] = charts.timeline(ctx["timeline_df"], datetime.date.today(), weeks=None)
    # HTMX requests for the table fragment receive only the partial.
    if request.headers.get("HX-Request") and request.query_params.get("fragment") == "results":
        return _page(request, "_schedule_results.html", "schedule", **ctx)
    return _page(request, "schedule.html", "schedule", **ctx)


# ── Garden Planner ──────────────────────────────────────────────────────────
@app.get("/planner", response_class=HTMLResponse)
def planner(request: Request, year: int | None = None,
            plant: str | None = None, width: float = 4.0, length: float = 8.0):
    year = year or views.default_year()
    ctx = views.planner_context(year)
    ctx["bed_charts"] = [
        (bv, charts.bed_layout(bv, ctx["companion"], include_js=(i == 0)))
        for i, bv in enumerate(ctx["bed_views"])
    ]
    ctx["spacing"] = views.spacing_context(year, plant, width, length)
    sun = views.sunlight_context(year)
    ctx["sun_groups"] = sun["groups"]
    ctx["sun_chart"] = charts.sunlight_bar(sun["sun_counts"], include_js=not ctx["bed_charts"])
    return _page(request, "planner.html", "planner", **ctx)


@app.get("/planner/spacing", response_class=HTMLResponse)
def planner_spacing(request: Request, year: int, plant: str | None = None,
                    width: float = 4.0, length: float = 8.0):
    ctx = views.spacing_context(year, plant, width, length)
    return _page(request, "_spacing_results.html", "planner", spacing=ctx)


@app.post("/planner/beds")
def planner_beds_save(
    name: str = Form(...), width: float = Form(4.0), length: float = Form(8.0),
    type: str = Form("Raised Bed"), sun: str = Form("Full Sun (6+ hrs)"),
    plants: list[str] = Form(default=[]), original_name: str = Form(""),
    year: int = Form(...),
):
    repo.upsert_garden_bed(
        {"name": name, "width": width, "length": length, "type": type, "sun": sun,
         "plants": plants},
        original_name=original_name or None,
    )
    return RedirectResponse(f"/planner?year={year}", status_code=303)


@app.post("/planner/beds/delete")
def planner_beds_delete(name: str = Form(...), year: int = Form(...)):
    repo.delete_garden_bed(name)
    return RedirectResponse(f"/planner?year={year}", status_code=303)


# ── Database Manager ──────────────────────────────────────────────────────────
@app.get("/database", response_class=HTMLResponse)
def database(request: Request, year: int | None = None, search: str = "",
             season: str = "All", method: str = "All", frost: str = "All"):
    year = year or views.default_year()
    ctx = views.database_context(year, search, season, method, frost)
    ctx["companions"] = views.companion_stats_context(year)["stats"]
    ctx["harvests"] = repo.list_harvests()
    ctx["variants"] = sorted(repo.get_seeds_df(year)["Display Name"].unique())
    ctx["today"] = datetime.date.today()
    if request.headers.get("HX-Request") and request.query_params.get("fragment") == "seeds":
        return _page(request, "_seed_table.html", "database", **ctx)
    return _page(request, "database.html", "database", **ctx)


# ── Seed CRUD (HTMX inline editing) ──
_SEED_FORM_FIELDS = [
    "seed", "variant", "brand", "season", "sun", "frost", "planting_method",
    "packet_year", "days_to_maturity", "days_after_transplant", "per_square",
    "transplant_delta", "last_frost_delta", "start_indoors", "transplant_sow",
    "plant_this_year",
]


async def _seed_fields(request: Request) -> dict:
    form = await request.form()
    return {k: form.get(k) for k in _SEED_FORM_FIELDS}


@app.get("/database/seed/{seed_id}/edit", response_class=HTMLResponse)
def seed_edit_form(request: Request, seed_id: int, year: int):
    seed = repo.get_seed(seed_id)
    if not seed:
        return HTMLResponse("", status_code=404)
    return _page(request, "_seed_row_edit.html", "database", s=seed, year=year)


@app.get("/database/seed/{seed_id}", response_class=HTMLResponse)
def seed_row(request: Request, seed_id: int, year: int):
    seed = repo.get_seed(seed_id)
    if not seed:
        return HTMLResponse("")
    return _page(request, "_seed_row.html", "database", r=views.seed_display(seed), year=year)


@app.post("/database/seed", response_class=HTMLResponse)
async def seed_add(request: Request):
    fields = await _seed_fields(request)
    form = await request.form()
    year = int(form.get("year"))
    seed = repo.get_seed(repo.add_seed(year, fields))
    return _page(request, "_seed_row.html", "database", r=views.seed_display(seed), year=year)


@app.post("/database/seed/{seed_id}", response_class=HTMLResponse)
async def seed_update(request: Request, seed_id: int):
    fields = await _seed_fields(request)
    form = await request.form()
    year = int(form.get("year"))
    repo.update_seed(seed_id, fields)
    seed = repo.get_seed(seed_id)
    return _page(request, "_seed_row.html", "database", r=views.seed_display(seed), year=year)


@app.post("/database/seed/{seed_id}/delete", response_class=HTMLResponse)
def seed_delete(seed_id: int):
    repo.delete_seed(seed_id)
    return HTMLResponse("")  # outerHTML swap removes the row


# ── Companion Plants ──────────────────────────────────────────────────────────
@app.get("/companions", response_class=HTMLResponse)
def companions(request: Request, year: int | None = None, plant: str | None = None,
               a: str | None = None, b: str | None = None,
               mp: list[str] | None = Query(default=None)):
    year = year or views.default_year()
    lookup = views.companion_lookup_context(year, plant, a, b)
    matrix = views.companion_matrix_context(year, mp)
    matrix["matrix_html"] = charts.companion_matrix(
        matrix["z"], matrix["labels"], matrix["hover"]
    ) if len(matrix["selected"]) >= 2 else charts.empty("Select at least 2 plants.")
    fragment = request.query_params.get("fragment")
    if request.headers.get("HX-Request") and fragment == "lookup":
        return _page(request, "_companion_lookup.html", "companions", lookup=lookup)
    if request.headers.get("HX-Request") and fragment == "matrix":
        return _page(request, "_companion_matrix.html", "companions", matrix=matrix)
    stats = views.companion_stats_context(year)["stats"]
    return _page(request, "companions.html", "companions",
                 lookup=lookup, matrix=matrix, stats=stats,
                 year=year, years=lookup["years"])


# ── Analytics ─────────────────────────────────────────────────────────────────
@app.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request, year: int | None = None,
              seed_cost: float = 150.0, supplies_cost: float = 100.0):
    year = year or views.default_year()
    harvest = views.analytics_harvest_context(year)
    harvest["harvest_bar"] = charts.harvest_bar(harvest["plant_totals"], harvest["companion"])
    harvest["harvest_line"] = (
        charts.harvest_line(harvest["daily"], harvest["companion"], include_js=False)
        if len(harvest["daily"]) > 1 else ""
    )
    insights = views.analytics_insights_context(year)
    insights["activity_html"] = charts.monthly_activity(insights["merged"], include_js=False)
    insights["days_html"] = charts.days_histogram(insights["days_numeric"], include_js=False)
    insights["frost_html"] = charts.frost_pie(insights["frost_counts"], include_js=False)
    cost = views.analytics_cost_context(year, None, seed_cost, supplies_cost)
    if cost.get("has_data"):
        cost["value_html"] = charts.value_bar(cost["cost_df"], cost["companion"], include_js=False)
    return _page(request, "analytics.html", "analytics",
                 harvest=harvest, insights=insights, cost=cost,
                 year=year, years=harvest["years"])


@app.get("/analytics/cost", response_class=HTMLResponse)
def analytics_cost(request: Request, year: int, seed_cost: float = 150.0,
                   supplies_cost: float = 100.0):
    cost = views.analytics_cost_context(year, None, seed_cost, supplies_cost)
    if cost.get("has_data"):
        cost["value_html"] = charts.value_bar(cost["cost_df"], cost["companion"], include_js=False)
    return _page(request, "_cost_results.html", "analytics", cost=cost)


# ── Harvest mutations (shared by Database + Analytics) ──
@app.post("/harvest/add")
def harvest_add(
    date: str = Form(...), plant: str = Form(...), variant: str = Form(""),
    quantity_kg: float = Form(...), notes: str = Form(""),
    next: str = Form("/analytics"),
):
    repo.add_harvest(date, plant, variant, quantity_kg, notes)
    return RedirectResponse(next, status_code=303)


@app.post("/harvest/delete")
def harvest_delete(harvest_id: int = Form(...), next: str = Form("/analytics")):
    repo.delete_harvest(harvest_id)
    return RedirectResponse(next, status_code=303)
