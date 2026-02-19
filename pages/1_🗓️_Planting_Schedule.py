"""
Page 1 — Planting Schedule (bed-aware, progress-tracking)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import (
    STATUS_COLORS,
    STATUS_LABELS,
    STATUS_OPTIONS,
    bed_for_plant,
    get_plant_status,
    load_garden_beds,
    load_progress,
    load_seeds_df,
    save_progress,
    setup_page,
    sidebar_nav,
)

setup_page("Planting Schedule", "🗓️")
sidebar_nav()

st.title("🗓️ Planting Schedule")
st.caption("Bed-aware growing season timeline with progress tracking.")

# ─── Load data ────────────────────────────────────────────────────────────────
year = 2026  # Default year
df_full = load_seeds_df(year)
beds = load_garden_beds()
progress = load_progress(year)
today = datetime.date.today()

# Build a plant→bed lookup from garden_beds.json
bed_lookup: dict[str, str] = {}
for bed in beds:
    for p in bed.get("plants", []):
        # p is a seed-family name (e.g. "Tomato")
        # Map every matching display_name row
        for dn in df_full[df_full["Seed"] == p]["Display Name"].unique():
            bed_lookup[dn] = bed["name"]
# Override with any per-plant override stored in progress
for dn, pdata in progress.items():
    if pdata.get("bed"):
        bed_lookup[dn] = pdata["bed"]

# Attach bed column to the full dataframe
df_full["Bed"] = df_full["Display Name"].map(bed_lookup).fillna("Unassigned")

# ─── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filters")

year = st.sidebar.number_input(
    "Growing Year", min_value=2020, max_value=2030, value=2025, step=1
)
season_start = f"{year}-01-01"
season_end   = f"{year}-10-13"

# ── Bed filter ──
bed_names = sorted({b["name"] for b in beds}) if beds else []
if bed_names:
    bed_filter_opts = ["All Beds"] + bed_names + ["Unassigned"]
    sel_beds = st.sidebar.multiselect(
        "🛏️ Beds", bed_names + ["Unassigned"], default=bed_names + ["Unassigned"]
    )
    df = df_full[df_full["Bed"].isin(sel_beds)].copy() if sel_beds else df_full.copy()
else:
    df = df_full.copy()
    st.sidebar.info("No beds defined yet — go to Garden Planner to create beds.")

# ── Standard filters ──
if "Season" in df.columns:
    seasons = sorted(df["Season"].dropna().unique())
    sel_seasons = st.sidebar.multiselect("Season", seasons, default=seasons)
    df = df[df["Season"].isin(sel_seasons)]

if "Frost" in df.columns:
    frost_vals = sorted(df["Frost"].dropna().unique())
    sel_frost = st.sidebar.multiselect("Frost Tolerance", frost_vals, default=frost_vals)
    df = df[df["Frost"].isin(sel_frost)]

methods = sorted(df["Planting Method"].dropna().unique())
sel_methods = st.sidebar.multiselect("Planting Method", methods, default=methods)
df = df[df["Planting Method"].isin(sel_methods)]

seeds = sorted(df["Display Name"].unique())
sel_seeds = st.sidebar.multiselect("Plants", seeds, default=seeds)
df = df[df["Display Name"].isin(sel_seeds)]

show_today  = st.sidebar.checkbox("Show today line", value=True)
show_weeks  = st.sidebar.checkbox("Show week shading", value=True)
color_by    = st.sidebar.radio("Color timeline by", ["Planting Method", "Bed", "Progress"], index=0)
group_by    = st.sidebar.radio("Group rows by", ["Individual Plant", "Seed Family", "Bed"], index=0)

st.sidebar.markdown("---")
total_shown   = df["Display Name"].nunique()
done_count    = sum(1 for dn in df["Display Name"].unique()
                    if get_plant_status(dn, progress)["transplant_status"] == "done")
st.sidebar.metric("Varieties shown", total_shown)
if total_shown:
    st.sidebar.progress(done_count / total_shown, text=f"{done_count}/{total_shown} fully done")

# ─── Guard ────────────────────────────────────────────────────────────────────
if df.empty:
    st.warning("No plants match your filters. Adjust sidebar selections.")
    st.stop()

# ─── Build plotting dataframe ─────────────────────────────────────────────────
if group_by == "Seed Family":
    df_plot = (
        df.groupby(["Seed", "Planting Method"])
        .agg({"Start Date": "min", "End Date": "max", "Bed": "first"})
        .reset_index()
        .rename(columns={"Seed": "Display Name"})
    )
elif group_by == "Bed":
    df_plot = (
        df.groupby(["Bed", "Planting Method"])
        .agg({"Start Date": "min", "End Date": "max"})
        .reset_index()
        .rename(columns={"Bed": "Display Name"})
    )
else:
    df_plot = df.copy()

# Attach progress status to df_plot
df_plot["start_status"]      = df_plot["Display Name"].apply(lambda n: get_plant_status(n, progress)["start_status"])
df_plot["transplant_status"] = df_plot["Display Name"].apply(lambda n: get_plant_status(n, progress)["transplant_status"])
df_plot["Overall Status"]    = df_plot.apply(
    lambda r: "done" if r["transplant_status"] == "done"
    else ("in_progress" if r["start_status"] in ("in_progress", "done") else "not_started"),
    axis=1,
)
df_plot["Status Label"] = df_plot["Overall Status"].map(STATUS_LABELS)

ordered = (
    df_plot.groupby("Display Name")["Start Date"]
    .min()
    .sort_values()
    .index.tolist()
)

# ─── Colour mapping ───────────────────────────────────────────────────────────
if color_by == "Bed":
    color_col = "Bed"
    color_map = {}   # auto-generated by plotly
elif color_by == "Progress":
    color_col = "Status Label"
    color_map = {v: STATUS_COLORS[k] for k, v in STATUS_LABELS.items()}
else:
    color_col = "Planting Method"
    color_map = {"Transplant": "#4CAF50", "Direct Sow": "#FF9800"}

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab_timeline, tab_progress, tab_beds, tab_calendar, tab_list = st.tabs([
    "📊 Timeline",
    "✏️ Update Progress",
    "🛏️ Bed Progress",
    "📆 Monthly Calendar",
    "📋 Task List",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TIMELINE
# ══════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    # ── For "Progress" mode, split each plant into TWO adjacent segments:
    #    Segment 1 (Start/Sow phase):      Start Date → End Date,  coloured by start_status
    #    Segment 2 (Transplant/Grow phase): End Date  → End Date+14d, coloured by transplant_status
    # For other colour modes, use the original single bar.
    if color_by == "Progress":
        seg_rows = []
        for _, row in df_plot.iterrows():
            dn     = row["Display Name"]
            start  = row["Start Date"]
            end    = row["End Date"]
            ss     = row["start_status"]
            ts     = row["transplant_status"]
            method = row.get("Planting Method", "")
            bed_nm = row.get("Bed", "Unassigned")

            if pd.notna(start) and pd.notna(end):
                seg_rows.append({
                    "Display Name": dn,
                    "Phase": "🌱 Sow / Indoors",
                    "Start Date": start,
                    "End Date": end,
                    "Status": STATUS_LABELS[ss],
                    "Planting Method": method,
                    "Bed": bed_nm,
                })
            if pd.notna(end):
                grow_end = end + pd.Timedelta(days=14)
                seg_rows.append({
                    "Display Name": dn,
                    "Phase": "🌿 Transplant / Outdoor",
                    "Start Date": end,
                    "End Date": grow_end,
                    "Status": STATUS_LABELS[ts],
                    "Planting Method": method,
                    "Bed": bed_nm,
                })

        df_tl    = pd.DataFrame(seg_rows)
        tl_color = "Status"
        tl_cmap  = {v: STATUS_COLORS[k] for k, v in STATUS_LABELS.items()}
        tl_hover = ["Phase", "Planting Method", "Bed"]
        legend_title = "Progress Status"
    else:
        df_tl    = df_plot.copy()
        tl_color = color_col
        tl_cmap  = color_map if color_map else None
        tl_hover = [c for c in ["Planting Method", "Bed", "Status Label"] if c in df_tl.columns]
        legend_title = color_col

    fig = px.timeline(
        df_tl,
        x_start="Start Date",
        x_end="End Date",
        y="Display Name",
        color=tl_color,
        color_discrete_map=tl_cmap,
        title="Growing Season Planting Schedule",
        labels={"Display Name": "Plant", "Planting Method": "Method"},
        category_orders={"Display Name": ordered},
        hover_data=tl_hover,
    )

    num = df_plot["Display Name"].nunique()
    fig.update_layout(
        height=max(550, 38 * num),
        margin=dict(l=200, r=20, t=45, b=20),
        yaxis=dict(automargin=True),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="",
        legend_title_text=legend_title,
    )
    fig.update_xaxes(range=[season_start, season_end], rangeslider_visible=True)

    if show_today:
        fig.add_shape(
            type="line",
            x0=str(today), x1=str(today),
            y0=0, y1=1, xref="x", yref="paper",
            line=dict(color="red", dash="dot", width=2),
        )
        fig.add_annotation(
            x=str(today), y=1, xref="x", yref="paper",
            text=f"Today ({today.strftime('%b %d')})",
            showarrow=False, font=dict(color="red", size=11), yanchor="bottom",
        )

    if show_weeks:
        cur = pd.Timestamp(season_start)
        end_ts = pd.Timestamp(season_end)
        shade = True
        while cur < end_ts:
            nxt = cur + pd.Timedelta(days=7)
            if shade:
                fig.add_vrect(x0=cur, x1=nxt, fillcolor="LightGrey",
                              opacity=0.13, layer="below", line_width=0)
            shade = not shade
            cur = nxt

    # In Progress mode: annotate each plant's transplant point with its status icon
    if color_by == "Progress":
        for _, row in df_plot.iterrows():
            if pd.notna(row["End Date"]):
                icon = {"done": "✅", "in_progress": "🔄", "skipped": "⏭️"}.get(
                    row["transplant_status"], ""
                )
                if icon:
                    fig.add_annotation(
                        x=row["End Date"], y=row["Display Name"],
                        xref="x", yref="y",
                        text=icon, showarrow=False,
                        font=dict(size=11), xanchor="center",
                    )
    else:
        # For non-progress modes, mark fully-done plants with ✅
        for _, row in df_plot.iterrows():
            if row["Overall Status"] == "done" and pd.notna(row["End Date"]):
                fig.add_annotation(
                    x=row["End Date"], y=row["Display Name"],
                    xref="x", yref="y",
                    text="✅", showarrow=False,
                    font=dict(size=12), xanchor="left",
                )

    st.plotly_chart(fig, use_container_width=True)

    if color_by == "Progress":
        st.caption(
            "Each plant shows **two segments**: "
            "🌱 Sow/Indoors phase (left) → 🌿 Transplant/Outdoor phase (right). "
            "Colour = progress status for that phase."
        )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_data = df_plot[["Display Name", "Planting Method", "Start Date", "End Date",
                             "Status Label"]].to_csv(index=False)
        st.download_button("⬇️ Download Schedule CSV", csv_data,
                           file_name=f"planting_schedule_{year}.csv", mime="text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — UPDATE PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
with tab_progress:
    st.subheader("✏️ Update Planting Progress")
    st.caption("Track what you've started, transplanted, or completed for each plant.")

    # Group by bed for easier management
    display_names = sorted(df["Display Name"].unique())

    # Filter controls
    prog_filter = st.selectbox(
        "Show plants:",
        ["All", "⬜ Not Started", "🔄 In Progress", "✅ Done", "⏭️ Skipped", "🛏️ In a Bed"],
        key="prog_filter",
    )

    # Build list filtered by selected status
    filtered_names = []
    for dn in display_names:
        ps = get_plant_status(dn, progress)
        overall = "done" if ps["transplant_status"] == "done" else (
            "in_progress" if ps["start_status"] in ("in_progress", "done") else ps["start_status"]
        )
        label = STATUS_LABELS.get(overall, "⬜ Not Started")
        if prog_filter == "All":
            filtered_names.append(dn)
        elif prog_filter == "🛏️ In a Bed" and bed_lookup.get(dn, "Unassigned") != "Unassigned":
            filtered_names.append(dn)
        elif prog_filter.split(" ", 1)[-1] in label:
            filtered_names.append(dn)

    if not filtered_names:
        st.info("No plants match this filter.")
    else:
        # Group by bed for display
        by_bed: dict[str, list[str]] = {}
        for dn in filtered_names:
            b = bed_lookup.get(dn, "Unassigned")
            by_bed.setdefault(b, []).append(dn)

        for bed_label, plant_names in sorted(by_bed.items()):
            with st.expander(f"🛏️ {bed_label} ({len(plant_names)} plants)", expanded=True):
                for dn in plant_names:
                    ps = get_plant_status(dn, progress)
                    row = df[df["Display Name"] == dn].iloc[0] if not df[df["Display Name"] == dn].empty else None

                    start_date_str = row["Start Date"].strftime("%b %d") if row is not None and pd.notna(row["Start Date"]) else "N/A"
                    end_date_str   = row["End Date"].strftime("%b %d") if row is not None and pd.notna(row["End Date"]) else "N/A"
                    method         = row["Planting Method"] if row is not None else ""
                    bg             = STATUS_COLORS.get(ps["start_status"], "#f5f5f5")

                    st.markdown(
                        f'<div style="background:{bg}; border-radius:6px; padding:6px 10px; '
                        f'margin-bottom:2px; font-size:0.85rem;">'
                        f'<b>{dn}</b> &nbsp;|&nbsp; {method} &nbsp;|&nbsp; '
                        f'Sow: {start_date_str} → Transplant: {end_date_str}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
                    with c1:
                        start_idx = STATUS_OPTIONS.index(ps["start_status"])
                        new_start_status = st.selectbox(
                            "Start/Sow Status",
                            options=STATUS_OPTIONS,
                            format_func=lambda x: STATUS_LABELS[x],
                            index=start_idx,
                            key=f"ss_{dn}",
                            label_visibility="collapsed",
                        )
                    with c2:
                        trans_idx = STATUS_OPTIONS.index(ps["transplant_status"])
                        new_trans_status = st.selectbox(
                            "Transplant Status",
                            options=STATUS_OPTIONS,
                            format_func=lambda x: STATUS_LABELS[x],
                            index=trans_idx,
                            key=f"ts_{dn}",
                            label_visibility="collapsed",
                        )
                    with c3:
                        # Bed assignment override
                        all_bed_opts = ["Unassigned"] + bed_names
                        current_bed  = ps["bed"] or bed_lookup.get(dn, "Unassigned")
                        bed_idx      = all_bed_opts.index(current_bed) if current_bed in all_bed_opts else 0
                        new_bed = st.selectbox(
                            "Bed",
                            options=all_bed_opts,
                            index=bed_idx,
                            key=f"bed_{dn}",
                            label_visibility="collapsed",
                        )
                    with c4:
                        new_notes = st.text_input(
                            "Notes",
                            value=ps["notes"],
                            key=f"notes_{dn}",
                            placeholder="Notes…",
                            label_visibility="collapsed",
                        )

                    # Auto-save whenever any value changes
                    existing = progress.get(dn, {})
                    if (
                        new_start_status != ps["start_status"]
                        or new_trans_status != ps["transplant_status"]
                        or new_notes != ps["notes"]
                        or new_bed != (ps["bed"] or bed_lookup.get(dn, "Unassigned"))
                    ):
                        updated = {
                            **existing,
                            "start_status": new_start_status,
                            "transplant_status": new_trans_status,
                            "notes": new_notes,
                            "bed": new_bed if new_bed != "Unassigned" else "",
                        }
                        progress[dn] = updated
                        save_progress(progress, year)
                        st.rerun()

                    st.markdown("---" if dn != plant_names[-1] else "")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BED PROGRESS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_beds:
    st.subheader("🛏️ Bed-by-Bed Progress")

    if not beds:
        st.info("No garden beds defined yet. Go to **Garden Planner** to create beds.")
    else:
        for bed in beds:
            bed_plant_seeds = bed.get("plants", [])
            # Get all display names that belong to this bed (by seed family)
            bed_display_names = []
            for seed_fam in bed_plant_seeds:
                bed_display_names += list(df_full[df_full["Seed"] == seed_fam]["Display Name"].unique())
            # Also include any plants manually assigned via progress override
            for dn, pdata in progress.items():
                if pdata.get("bed") == bed["name"] and dn not in bed_display_names:
                    bed_display_names.append(dn)

            if not bed_display_names:
                with st.expander(f"🛏️ {bed['name']} — no plants assigned"):
                    st.info("Assign plants via the Garden Planner or Update Progress tab.")
                continue

            # Compute status counts
            statuses = {
                "done": 0, "in_progress": 0, "not_started": 0, "skipped": 0
            }
            for dn in bed_display_names:
                ps = get_plant_status(dn, progress)
                t = ps["transplant_status"]
                s = ps["start_status"]
                if t == "done":
                    statuses["done"] += 1
                elif t == "skipped" or s == "skipped":
                    statuses["skipped"] += 1
                elif s in ("in_progress", "done"):
                    statuses["in_progress"] += 1
                else:
                    statuses["not_started"] += 1

            total_bed = len(bed_display_names)
            done_pct = int(statuses["done"] / total_bed * 100) if total_bed else 0
            ip_pct   = int(statuses["in_progress"] / total_bed * 100) if total_bed else 0

            with st.expander(
                f"🛏️ **{bed['name']}** — {bed['width']}×{bed['length']} ft | "
                f"{done_pct}% done | {len(bed_display_names)} varieties",
                expanded=True,
            ):
                # Progress bar
                bc1, bc2 = st.columns([3, 1])
                with bc1:
                    bar_html = (
                        f'<div style="height:14px; background:#e0e0e0; border-radius:7px; overflow:hidden;">'
                        f'<div style="height:100%; width:{done_pct + ip_pct}%; background:#a5d6a7; border-radius:7px;">'
                        f'<div style="height:100%; width:{int(done_pct / (done_pct + ip_pct + 0.001) * 100)}%; background:#4CAF50; border-radius:7px;"></div>'
                        f'</div></div>'
                        f'<div style="font-size:0.78rem; color:#555; margin-top:3px;">'
                        f'✅ {statuses["done"]} done &nbsp;·&nbsp; '
                        f'🔄 {statuses["in_progress"]} in progress &nbsp;·&nbsp; '
                        f'⬜ {statuses["not_started"]} not started &nbsp;·&nbsp; '
                        f'⏭️ {statuses["skipped"]} skipped'
                        f'</div>'
                    )
                    st.markdown(bar_html, unsafe_allow_html=True)
                with bc2:
                    st.markdown(f"**{bed['sun']}**  \n{bed['type']}")

                st.markdown("")

                # Plants table
                plant_rows = []
                for dn in sorted(bed_display_names):
                    ps  = get_plant_status(dn, progress)
                    row = df_full[df_full["Display Name"] == dn]
                    start_str = row["Start Date"].iloc[0].strftime("%b %d") if not row.empty and pd.notna(row["Start Date"].iloc[0]) else "—"
                    end_str   = row["End Date"].iloc[0].strftime("%b %d")   if not row.empty and pd.notna(row["End Date"].iloc[0])   else "—"
                    method    = row["Planting Method"].iloc[0] if not row.empty else "—"
                    plant_rows.append({
                        "Plant":        dn,
                        "Method":       method,
                        "Sow Date":     start_str,
                        "Transplant":   end_str,
                        "Start Status": STATUS_LABELS.get(ps["start_status"], "—"),
                        "Final Status": STATUS_LABELS.get(ps["transplant_status"], "—"),
                        "Notes":        ps["notes"],
                    })

                bed_df = pd.DataFrame(plant_rows)
                st.dataframe(bed_df, use_container_width=True, hide_index=True)

                # Upcoming tasks for this bed
                upcoming_bed = []
                for dn in bed_display_names:
                    ps  = get_plant_status(dn, progress)
                    row = df_full[df_full["Display Name"] == dn]
                    if row.empty:
                        continue
                    start = row["Start Date"].iloc[0]
                    end   = row["End Date"].iloc[0]
                    if ps["start_status"] == "not_started" and pd.notna(start):
                        d = (start.date() - today).days
                        if -7 <= d <= 21:
                            upcoming_bed.append(f"{'⚠️' if d < 0 else '🔜'} **{dn}**: Sow by {start.strftime('%b %d')} ({abs(d)}d {'ago' if d < 0 else 'away'})")
                    if ps["transplant_status"] not in ("done", "skipped") and pd.notna(end):
                        d = (end.date() - today).days
                        if -7 <= d <= 21:
                            upcoming_bed.append(f"{'⚠️' if d < 0 else '🔜'} **{dn}**: Transplant by {end.strftime('%b %d')} ({abs(d)}d {'ago' if d < 0 else 'away'})")

                if upcoming_bed:
                    st.markdown("**📅 Upcoming tasks (±3 weeks):**")
                    for task in upcoming_bed:
                        st.markdown(f"&nbsp;&nbsp;{task}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MONTHLY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_calendar:
    st.subheader("Monthly Planting Calendar")
    months      = list(range(1, 11))
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct"]

    all_plants  = sorted(df["Display Name"].unique())
    matrix_data = []
    for plant in all_plants:
        ps  = get_plant_status(plant, progress)
        overall_done = ps["transplant_status"] == "done"
        row_data = {"Plant": plant, "Bed": bed_lookup.get(plant, "—")}
        prows = df[df["Display Name"] == plant]
        for m, mname in zip(months, month_names):
            active = False
            for _, pr in prows.iterrows():
                start = pr["Start Date"]
                end   = pr["End Date"]
                if pd.notna(start) and pd.notna(end):
                    ms = pd.Timestamp(year=year, month=m, day=1)
                    me = ms + pd.offsets.MonthEnd(0)
                    if start <= me and end >= ms:
                        active = True
            if active:
                row_data[mname] = "✅" if overall_done else "🟩"
            else:
                row_data[mname] = ""
        matrix_data.append(row_data)

    matrix_df = pd.DataFrame(matrix_data)
    st.dataframe(matrix_df, use_container_width=True, hide_index=True)
    st.caption("🟩 = Scheduled  ✅ = Done (transplant complete)")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TASK LIST
# ══════════════════════════════════════════════════════════════════════════════
with tab_list:
    st.subheader("📋 All Planting Tasks")

    all_tasks = []
    for _, row in df.iterrows():
        dn     = row["Display Name"]
        method = row.get("Planting Method", "")
        start  = row["Start Date"]
        end    = row["End Date"]
        bed_nm = bed_lookup.get(dn, "Unassigned")
        ps     = get_plant_status(dn, progress)

        if pd.notna(start):
            days_diff = (start.date() - today).days
            task_status = (
                "✅ Done" if ps["start_status"] == "done"
                else ("⏭️ Skipped" if ps["start_status"] == "skipped"
                      else ("🔄 In Progress" if ps["start_status"] == "in_progress"
                            else ("⚠️ Overdue" if days_diff < 0 else ("🔜 Soon" if days_diff <= 14 else "⏳ Upcoming"))))
            )
            all_tasks.append({
                "Plant": dn, "Bed": bed_nm,
                "Action": "Start Indoors / Sow",
                "Date": start.strftime("%b %d, %Y"),
                "Days": days_diff, "Method": method,
                "Status": task_status,
                "Notes": ps["notes"],
            })

        if pd.notna(end):
            days_diff = (end.date() - today).days
            task_status = (
                "✅ Done" if ps["transplant_status"] == "done"
                else ("⏭️ Skipped" if ps["transplant_status"] == "skipped"
                      else ("🔄 In Progress" if ps["start_status"] in ("in_progress", "done")
                            else ("⚠️ Overdue" if days_diff < 0 else ("🔜 Soon" if days_diff <= 14 else "⏳ Upcoming"))))
            )
            all_tasks.append({
                "Plant": dn, "Bed": bed_nm,
                "Action": "Transplant / Direct Sow",
                "Date": end.strftime("%b %d, %Y"),
                "Days": days_diff, "Method": method,
                "Status": task_status,
                "Notes": ps["notes"],
            })

    task_df = pd.DataFrame(all_tasks).sort_values("Days").reset_index(drop=True)
    task_df["Days Label"] = task_df["Days"].apply(
        lambda d: "Today" if d == 0 else (f"In {d}d" if d > 0 else f"{abs(d)}d ago")
    )

    # ── Filters ──
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        status_filter = st.selectbox(
            "Status filter",
            ["All", "🔜 Soon / Overdue", "🔄 In Progress", "⏳ Upcoming", "✅ Done", "⏭️ Skipped"],
        )
    with lc2:
        bed_task_filter = st.multiselect(
            "Bed filter",
            ["All"] + sorted(task_df["Bed"].unique().tolist()),
            default=["All"],
        )
    with lc3:
        sort_by = st.selectbox("Sort by", ["Date", "Plant", "Bed", "Status"])

    # Apply filters
    ftdf = task_df.copy()
    if status_filter == "🔜 Soon / Overdue":
        ftdf = ftdf[ftdf["Status"].isin(["🔜 Soon", "⚠️ Overdue"])]
    elif status_filter != "All":
        ftdf = ftdf[ftdf["Status"] == status_filter]

    if "All" not in bed_task_filter and bed_task_filter:
        ftdf = ftdf[ftdf["Bed"].isin(bed_task_filter)]

    sort_map = {"Date": "Days", "Plant": "Plant", "Bed": "Bed", "Status": "Status"}
    ftdf = ftdf.sort_values(sort_map[sort_by]).reset_index(drop=True)

    st.markdown(f"**{len(ftdf)} tasks** shown")
    st.dataframe(
        ftdf[["Status", "Days Label", "Plant", "Bed", "Action", "Date", "Method", "Notes"]],
        use_container_width=True,
        hide_index=True,
    )

    # Quick bulk actions
    st.markdown("---")
    st.subheader("⚡ Bulk Actions")
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("✅ Mark all overdue starts as Done"):
            changed = 0
            for _, r in task_df[
                (task_df["Action"] == "Start Indoors / Sow") & (task_df["Status"] == "⚠️ Overdue")
            ].iterrows():
                dn = r["Plant"]
                ps = get_plant_status(dn, progress)
                if ps["start_status"] != "done":
                    progress[dn] = {**progress.get(dn, {}), "start_status": "done"}
                    changed += 1
            if changed:
                save_progress(progress, year)
                st.success(f"Marked {changed} plants as started.")
                st.rerun()
    with bc2:
        if st.button("✅ Mark all overdue transplants as Done"):
            changed = 0
            for _, r in task_df[
                (task_df["Action"] == "Transplant / Direct Sow") & (task_df["Status"] == "⚠️ Overdue")
            ].iterrows():
                dn = r["Plant"]
                ps = get_plant_status(dn, progress)
                if ps["transplant_status"] != "done":
                    progress[dn] = {**progress.get(dn, {}), "transplant_status": "done"}
                    changed += 1
            if changed:
                save_progress(progress, year)
                st.success(f"Marked {changed} plants as transplanted.")
                st.rerun()