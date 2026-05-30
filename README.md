# 🌿 Verti Garden Planner

A comprehensive gardening app for planning, tracking, and managing your growing
season. Built with **FastAPI + HTMX** (server-rendered, no JS build step),
**SQLModel/SQLite** for storage, and **Plotly** for charts.

## Features

| Page | Description |
|------|-------------|
| 🌿 **Dashboard** | At-a-glance overview: upcoming tasks, 6-week timeline, season summary |
| 🗓️ **Planting Schedule** | Full season timeline and task list with bed/season/method filters |
| 🌱 **Garden Planner** | Visual bed designer, spacing calculator, sunlight planner |
| 📊 **Database Manager** | Search/filter seeds, harvest log, companion reference |
| 🤝 **Companion Plants** | Compatibility lookup, interactive heatmap matrix, tips |
| 📈 **Analytics** | Harvest tracker, garden insights, cost/ROI analysis |

## Architecture

```
verti/                  # UI-agnostic data layer
├── db.py               # SQLite engine / session (VERTI_DB_PATH configurable)
├── models.py           # SQLModel ORM models
├── repository.py       # Data access (DataFrames / dicts) + CRUD
├── logic.py            # Pure horticulture helpers (spacing, companions, dates)
└── migrate.py          # One-off importer: flat files → SQLite

web/                    # FastAPI + HTMX UI
├── main.py             # App, routes, HTMX fragment endpoints, form handlers
├── views.py            # View-models (no framework deps)
├── charts.py           # Plotly figures rendered to HTML fragments
├── templates/          # Jinja templates + HTMX partials
└── static/             # Tailwind (CDN) + small CSS

data/
├── verti.db            # SQLite database (generated; git-ignored)
├── seeds/              # Per-year seed CSVs (migration source/backup)
├── companion_plants.json, garden_beds.json, planting_rules.json
├── progress/           # Per-year planting progress (migration source)
└── harvests/           # Harvest logs (migration source)
```

## Data layer

Data lives in a single **SQLite** database (`data/verti.db`) via a
[SQLModel](https://sqlmodel.tiangolo.com/) ORM. It is generated from the
committed flat files the first time you run the migration; those files remain in
the repo as the seed/backup.

```bash
uv run python -m verti.migrate          # build DB (idempotent — skips if present)
uv run python -m verti.migrate --force  # wipe and re-import from the flat files
```

The DB path is configurable with the `VERTI_DB_PATH` environment variable, so it
can point at a mounted volume in Docker / cloud deployments.

## Run locally

```bash
# With uv (recommended)
uv sync
uv run python -m verti.migrate          # first run only
uv run uvicorn web.main:app --reload    # http://localhost:8000

# Without uv
pip install -r requirements.txt
python -m verti.migrate
uvicorn web.main:app --reload
```

## Run with Docker (recommended for deployment)

The container runs the app and stores the database on a named volume, so data
survives restarts and redeploys — unlike a flat-file store on an ephemeral cloud
filesystem.

```bash
docker compose up --build      # http://localhost:8000
```

The entrypoint runs the migration on startup (idempotent) to build the database
from the bundled flat files into the volume. The DB location is controlled by
`VERTI_DB_PATH` (defaults to `/data/verti.db` in the container). This image runs
anywhere Docker does — a VPS, or a managed platform like Fly.io / Railway /
Render.

## Editing data

- **Seeds** — edit `data/seeds/<year>-seeds.csv` and re-run `verti.migrate
  --force`, or manage harvests/beds directly in the app.
- **Companion relationships / colors / spacing** — `data/companion_plants.json`.
- **Garden beds, harvests, planting progress** — created and edited in the app
  and stored in SQLite.
