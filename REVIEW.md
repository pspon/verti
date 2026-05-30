# Verti Garden Planner — Codebase Review

The repo recently went through a large modernization: it migrated from a
**flat-file + Streamlit** app to a **SQLite + SQLModel** data layer behind a
**FastAPI + HTMX** server-rendered UI, packaged for **Docker**. This review
covers the *current* state of that codebase.

---

## 1. What the app is (product summary)

Verti is a **single-user garden-planning web app** for a Toronto-area grower
(last frost hardcoded to May 9). It manages a seed catalogue per growing season
and helps plan, schedule, lay out, and measure a vegetable garden. Six pages:

| Page | Purpose |
|------|---------|
| 🌿 Dashboard | Season metrics, upcoming/overdue tasks (next 14 days), 6-week timeline, season/method/brand breakdowns |
| 🗓️ Planting Schedule | Full-season Plotly timeline + task list, filterable by season/method/bed, with progress display |
| 🌱 Garden Planner | Bed designer (top-down schematic), square-foot spacing/yield calculator, sunlight grouping |
| 📊 Database Manager | Search/filter seed catalogue, inline HTMX CRUD on seeds, harvest log, companion reference |
| 🤝 Companion Plants | Good/bad lookup, interactive compatibility heatmap, per-plant stats |
| 📈 Analytics | Harvest tracker, planting-activity & days-to-harvest insights, cost/ROI estimate |

### Business / user requirements fulfilled

- **Seed inventory per season** — multi-year seed catalogue (`season_year`), full CRUD, search & filter.
- **Frost-relative scheduling** — start-indoors / transplant / direct-sow dates, "Direct Sow = sow − 3 days" rule preserved.
- **Task surfacing** — dashboard computes upcoming (0–14 day) and recently-overdue (−3 day) tasks.
- **Spatial planning** — square-foot-gardening math (`plants_per_sqft`, `plants_in_bed`) + visual bed layout.
- **Companion planting** — good/bad relationships, pairwise lookup, NxN heatmap, per-bed compatibility warnings.
- **Yield & ROI tracking** — harvest log, totals, market-value estimate vs. seed/supplies investment.
- **Durable storage & deployment** — SQLite on a mounted Docker volume; `VERTI_DB_PATH` configurable; idempotent migration from the committed flat files.

The architecture is clean and the separation is genuinely good: `verti/`
(framework-agnostic data + logic) vs `web/` (FastAPI routes, view-models, Plotly
charts, Jinja/HTMX templates). View-models are pure functions, charts are pure
HTML builders, and the repository hides the ORM behind legacy-shaped
dicts/DataFrames. The HTMX fragment pattern (single endpoint returns full page or
partial based on `HX-Request` + `fragment`) is applied consistently.

---

## 2. Bugs & correctness issues

Ranked roughly by impact.

### 2.1 Harvest data has no year dimension — the Analytics/Database year selector is a lie
- **Where:** `verti/models.py` (`Harvest` has no `season_year`); `verti/repository.py` (`get_harvest_log`, `list_harvests` select *all* harvests); `web/views.py` (analytics contexts).
- **Problem:** `Harvest` carries no season/year. Every harvest query returns the entire table. So the Year dropdown on **Analytics** and **Database Manager** changes the seed/variant lists but the harvest totals, entry counts, "unique plants", charts, and ROI are **identical for every year**. A 2026 harvest shows up in the 2025 analytics and vice-versa.
- **Fix direction:** add `season_year` to `Harvest`, scope all harvest reads/writes by year, and pass the year through the add-harvest forms.

### 2.2 The two "Log a Harvest" forms write inconsistent data → split totals
- **Where:** `web/templates/database.html` vs `web/templates/analytics.html`.
- **Problem:** On **Analytics**, the harvest form sends `plant` = *family* ("Tomato") and `variant` = *display name* ("Tomato Sungold"). On **Database Manager**, the single dropdown sends `plant` = *display name* ("Tomato Sungold") and leaves `variant` empty. Analytics groups by `Plant`, so harvests logged from the two pages land in **different groups** ("Tomato" vs "Tomato Sungold"), fragmenting totals, charts, and ROI. Market-price lookup (`DEFAULT_PRICES`, keyed by family) also misses for the display-name rows.
- **Fix direction:** pick one contract (family in `plant`, variety in `variant`) and use it in both forms.

### 2.3 Progress tracking is read-only — a regression from the Streamlit app
- **Where:** schedule page renders `start_status`/`transplant_status` (`_schedule_results.html`) but there is **no endpoint** to change them. `repository.save_progress` and `logic.get_plant_status`/`STATUS_*` exist but are never called from `web/`.
- **Problem:** The Schedule page and dashboard advertise "progress tracking," yet a user cannot mark a plant as started/transplanted/done in the new UI. The only way status is ever set is via the one-time migration of the legacy `*_progress.json`. The "X fully done" metric and progress bar are therefore effectively frozen.
- **Fix direction:** add an HTMX endpoint to toggle/cycle status per plant and call `save_progress` (or a granular upsert).

### 2.4 The "Plant in <year>" flag is dead — unchecking it does nothing
- **Where:** `Seed.plant_this_year`, surfaced in the edit form, but never used as a filter in `dashboard_context`/`schedule_context`/timeline.
- **Problem:** Every seed in the CSV appears on the schedule/dashboard regardless of whether it's flagged for planting this year. In the legacy app this flag presumably scoped the active plan.
- **Aggravating naming bug:** the column is hardcoded as **`"Plant in 2025"`** everywhere — `migrate.py`, `repository.py` (output dict key), `_seed_from_row`. The 2026 CSV only works because it *also* uses the literal header `Plant in 2025` (both `2025-seeds.csv` and `2026-seeds.csv` share that header). This is fragile and misleading for any future year.

### 2.5 Open redirect on harvest mutations
- **Where:** `web/main.py` — `next: str = Form("/analytics")` then `RedirectResponse(next)`.
- **Problem:** The post-action redirect target comes straight from a form field with no validation. A crafted form can redirect the user to an external site after a POST. Low severity for a single-user app but trivially fixable: validate that `next` starts with `/`.

### 2.6 `get_seeds_df` silently substitutes another year's data
- **Where:** `repository.py`.
- **Problem:** If the requested year has no seeds, it falls back to the *earliest* available year's seeds but the page still labels everything with the requested year. With `default_year()` choosing from `available_years()` this is rare, but a hand-typed `?year=2030` will show 2025 data under a "2030" heading instead of an empty state.

### 2.7 Minor logic / edge cases
- **No-auth, full CRUD:** the app has no authentication. Anyone who can reach the port can edit or delete all seeds, beds, and harvests. Worth a note given the README recommends deploying to a public VPS / Fly.io / Railway.
- **`@app.on_event("startup")`** is deprecated in current FastAPI; prefer a `lifespan` handler.
- **Timeline window** excludes plants that have only an end date (NaT start → both mask clauses false). Edge case.
- **SpacingGuide null spacing:** `plants_per_sqft` guards `spacing_in <= 0`, but a `SpacingGuide` row with `spacing_in = None` would raise on the comparison; only the hardcoded default (12) is safe. Reachable only via malformed reference data.
- **Companion pair counting** divides good/bad counts by 2 assuming symmetry; contradictory data (A→good→B but B→bad→A) is miscounted. Data-quality edge case.

---

## 3. Dead code & cleanup (post-Streamlit residue)

The Streamlit UI and `utils/helpers.py` were removed, but a layer of helper
functions that only the old UI called is still present and unreferenced:

- `verti/logic.py`: `calculate_planting_dates`, `get_plant_status`, `bed_for_plant`, and the `STATUS_OPTIONS/LABELS/COLORS` constants (the templates re-define their own status-label dict inline in `_schedule_results.html`).
- `verti/repository.py`: `save_seeds_df`, `save_progress`, `save_planting_rules`, `save_harvest_log`, `save_garden_beds`, `upsert_planting_rule_deltas`.

(Verified by `git grep` — each is defined but has no caller outside its own
module.) These are bulk delete-then-reinsert "replace whole table" writers from
the file era; the live UI uses the granular `add_*/update_*/delete_*/upsert_*`
paths instead. Keeping them is harmless at runtime but is dead maintenance
surface.

`PlantingRule` / planting-rules import and `calculate_planting_dates` together
form a whole "compute dates from frost deltas" subsystem that nothing in the web
UI invokes — dates are read directly from the stored `start_indoors`/
`transplant_sow` columns. Either wire it up or drop it.

---

## 4. Documentation drift

- **`CLAUDE.md` is stale and now actively misleading.** It still describes a
  Streamlit multi-page app (`app.py`, `pages/1_…`, `utils/helpers.py`), flat-file
  storage, `@st.cache_data`, and `uv run streamlit run app.py`. None of that
  exists anymore. The README, by contrast, is accurate and good. CLAUDE.md should
  be rewritten to match the FastAPI/HTMX/SQLite reality.
- **No tests exist**, despite `views.py` and `logic.py` being explicitly written
  "so the logic stays testable." The harvest-grouping (2.2), year-scoping (2.1),
  and spacing math are exactly the kind of pure functions that would benefit.

---

## 5. Overall assessment

The modernization is well executed: a clean three-layer backend, a tidy and
consistent HTMX pattern, sensible Docker/volume deployment, and an idempotent
migration with a `--force` escape hatch. The product covers a coherent set of
real gardening workflows.

The most important issues are **data-model gaps that silently produce wrong
numbers** — harvests not scoped by year (2.1) and the two harvest forms writing
incompatible shapes (2.2) — followed by the **lost ability to update progress**
(2.3) and the **inert "plant this year" flag** (2.4). After those, the cleanup
is mostly removing post-migration dead code and fixing the stale `CLAUDE.md`.
