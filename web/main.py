"""FastAPI application entry point for the Verti Garden Planner web UI."""

from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
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


# ── Placeholder pages for sections not yet ported (Increment 3) ──
def _make_placeholder(section: str):
    label = next(n["label"] for n in views.NAV if n["key"] == section)

    def handler(request: Request):
        return _page(request, "_placeholder.html", section, title=label)

    return handler


for _section in ("planner", "database", "companions", "analytics"):
    app.get(f"/{_section}", response_class=HTMLResponse)(_make_placeholder(_section))
