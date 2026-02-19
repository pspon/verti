# 🌿 Verti Garden Planner

A comprehensive gardening app built with Streamlit for planning, tracking, and managing your growing season.

## Features

| Page | Description |
|------|-------------|
| 🏠 **Home Dashboard** | At-a-glance overview: upcoming tasks, 6-week timeline, season summary |
| 🗓️ **Planting Schedule** | Full season timeline, monthly calendar, and task list with filters |
| 🌿 **Garden Planner** | Visual bed designer, spacing calculator, sunlight planner |
| 📊 **Database Manager** | View, search, add, edit, delete seeds — import/export CSV & Excel |
| 🤝 **Companion Plants** | Compatibility lookup, interactive heatmap matrix, planting tips |
| 📈 **Analytics** | Harvest tracker, garden insights, cost/ROI analysis |

## Setup with uv

```bash
# Install uv (if not already installed)
pip install uv

# Install dependencies
uv sync

# Run the app
uv run streamlit run app.py
```

## Setup without uv

```bash
pip install -r requirements.txt
streamlit run app.py
```

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
├── utils/
│   ├── __init__.py
│   └── helpers.py              # Shared data loading & utilities
├── data/
│   ├── companion_plants.json   # Companion planting database
│   ├── garden_beds.json        # Saved garden bed layouts (auto-created)
│   └── harvest_log.csv         # Harvest log (auto-created)
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
