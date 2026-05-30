# 🌿 Verti Garden Planner

A comprehensive gardening app for planning, tracking, and managing your growing
season. Data is stored in **SQLite** (via SQLModel). There are two front-ends
sharing the same data layer during an ongoing migration:

* **FastAPI + HTMX** (`web/`) — the modern UI, Docker-deployable. Dashboard and
  Planting Schedule are ported; the remaining sections are being migrated.
* **Streamlit** (`app.py`, `pages/`) — the original UI, fully featured.

## Features

| Page | Description |
|------|-------------|
| 🏠 **Home Dashboard** | At-a-glance overview: upcoming tasks, 6-week timeline, season summary |
| 🗓️ **Planting Schedule** | Full season timeline, monthly calendar, and task list with filters |
| 🌿 **Garden Planner** | Visual bed designer, spacing calculator, sunlight planner |
| 📊 **Database Manager** | View, search, add, edit, delete seeds — import/export CSV & Excel |
| 🤝 **Companion Plants** | Compatibility lookup, interactive heatmap matrix, planting tips |
| 📈 **Analytics** | Harvest tracker, garden insights, cost/ROI analysis |

## Data layer

Data is stored in a single **SQLite** database (`data/verti.db`) via a
[SQLModel](https://sqlmodel.tiangolo.com/) ORM. The database is generated from
the committed flat files (`data/seeds/*.csv`, `data/*.json`) the first time you
run the migration; those files remain in the repo as the seed/backup.

```bash
# Build the DB from the flat files (idempotent — skips if data already present)
uv run python -m verti.migrate

# Re-import from scratch (wipes the DB first)
uv run python -m verti.migrate --force
```

The DB path is configurable with the `VERTI_DB_PATH` environment variable, so it
can point at a mounted volume in Docker / cloud deployments.

## Setup with uv

```bash
# Install uv (if not already installed)
pip install uv

# Install dependencies
uv sync

# Build the database from the flat files (first run only)
uv run python -m verti.migrate

# Run the app
uv run streamlit run app.py
```

## Setup without uv

```bash
pip install -r requirements.txt
python -m verti.migrate
streamlit run app.py
```

## Run the FastAPI + HTMX web UI

```bash
uv run python -m verti.migrate          # first run only
uv run uvicorn web.main:app --reload    # http://localhost:8000
```

## Run with Docker (recommended for deployment)

The container runs the FastAPI UI and stores the database on a named volume, so
data survives restarts and redeploys — unlike the previous flat-file approach on
ephemeral cloud filesystems.

```bash
docker compose up --build      # http://localhost:8000
```

The entrypoint runs the migration on startup (idempotent) to build the database
from the bundled flat files into the volume. The DB location is controlled by
`VERTI_DB_PATH` (defaults to `/data/verti.db` in the container). This image runs
anywhere Docker does — a VPS, or a managed platform like Fly.io / Railway /
Render.

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy**

> **Note:** Streamlit Cloud uses `requirements.txt` by default.  
> The `pyproject.toml` is for local development with `uv`.

## Project Structure

```
Verti/
├── app.py                      # Home dashboard (main entry point)
├── pages/
│   ├── 1_🗓️_Planting_Schedule.py
│   ├── 2_🌿_Garden_Planner.py
│   ├── 3_📊_Database_Manager.py
│   ├── 4_🤝_Companion_Plants.py
│   └── 5_📈_Analytics.py
├── verti/                      # UI-agnostic data layer (reused by Streamlit & the upcoming FastAPI UI)
│   ├── db.py                   # SQLite engine / session
│   ├── models.py               # SQLModel ORM models
│   ├── repository.py           # Data access (returns DataFrames / dicts)
│   └── migrate.py              # Import flat files → SQLite
├── utils/
│   ├── __init__.py
│   └── helpers.py              # Streamlit helpers (delegate to verti.repository)
├── data/
│   ├── verti.db                # SQLite database (generated; git-ignored)
│   ├── seeds/                  # Per-year seed CSVs (migration source/backup)
│   ├── companion_plants.json   # Companion planting database (migration source)
│   ├── garden_beds.json        # Garden bed layouts (migration source)
│   ├── progress/               # Per-year planting progress (migration source)
│   └── harvests/               # Harvest logs (migration source)
├── .streamlit/
│   └── config.toml             # Theme and server config
├── 2025-seeds.csv              # Your seed & planting data
├── pyproject.toml              # uv project config
├── requirements.txt            # Streamlit Cloud compatible deps
└── README.md
```

## Data Files

- **`2025-seeds.csv`** — Your main seed database. Edit directly or use the Database Manager page.
- **`data/companion_plants.json`** — Edit to add more companion planting relationships and plant colors.
- **`data/garden_beds.json`** — Auto-created when you save garden beds in the Garden Planner.
- **`data/harvest_log.csv`** — Auto-created when you log harvests in Analytics.
