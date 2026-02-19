"""
Page 2 — Garden Space Planner
Visual grid-based garden bed designer with spacing calculations and companion planting feedback.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import (
    companion_relationship,
    get_plant_color,
    get_spacing,
    load_companion_data,
    load_garden_beds,
    load_seeds_df,
    load_planting_rules,
    plants_in_bed,
    save_garden_beds,
    setup_page,
    sidebar_nav,
)

setup_page("Garden Planner", "🌿")
sidebar_nav()

st.title("🌿 Garden Space Planner")
st.caption("Design your beds, calculate spacing, and check companion planting compatibility.")

year = 2025  # Default year
df = load_seeds_df(year)
companion_data = load_companion_data()
beds = load_garden_beds()
rules = load_planting_rules()

# Unique plant list (seed family names)
plant_list = sorted(df["Seed"].unique())

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_beds, tab_spacing, tab_sunlight = st.tabs(
    ["🛏️ Bed Designer", "📏 Spacing Calculator", "☀️ Sunlight Planner"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BED DESIGNER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_beds:
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Add / Edit Bed")

        bed_name = st.text_input("Bed Name", value="Raised Bed 1")
        bed_width = st.number_input("Width (feet)", min_value=1.0, max_value=20.0, value=4.0, step=0.5)
        bed_length = st.number_input("Length (feet)", min_value=1.0, max_value=40.0, value=8.0, step=0.5)
        bed_type = st.selectbox("Bed Type", ["Raised Bed", "In-Ground", "Container", "Vertical"])
        sun_exposure = st.selectbox(
            "Sun Exposure", ["Full Sun (6+ hrs)", "Part Sun (3-6 hrs)", "Shade (<3 hrs)"]
        )

        # Plant selection for this bed
        selected_plants = st.multiselect(
            "Plants in this bed",
            plant_list,
            help="Select plants to assign to this bed",
        )

        if st.button("➕ Add / Update Bed", type="primary"):
            bed_entry = {
                "name": bed_name,
                "width": bed_width,
                "length": bed_length,
                "type": bed_type,
                "sun": sun_exposure,
                "plants": selected_plants,
            }
            # Update if name exists, else append
            existing = next((i for i, b in enumerate(beds) if b["name"] == bed_name), None)
            if existing is not None:
                beds[existing] = bed_entry
                st.success(f"Updated bed: **{bed_name}**")
            else:
                beds.append(bed_entry)
                st.success(f"Added bed: **{bed_name}**")
            save_garden_beds(beds)
            st.rerun()

        st.markdown("---")
        st.subheader("Saved Beds")
        if beds:
            for i, bed in enumerate(beds):
                with st.expander(f"🛏️ {bed['name']} ({bed['width']}×{bed['length']} ft)"):
                    st.write(f"**Type:** {bed['type']} | **Sun:** {bed['sun']}")
                    sq_ft = bed['width'] * bed['length']
                    st.write(f"**Area:** {sq_ft:.0f} sq ft")
                    if bed.get("plants"):
                        st.write(f"**Plants:** {', '.join(bed['plants'])}")
                    if st.button(f"🗑️ Remove", key=f"del_bed_{i}"):
                        beds.pop(i)
                        save_garden_beds(beds)
                        st.rerun()
        else:
            st.info("No beds added yet. Create one using the form above.")

    with col_right:
        st.subheader("🗺️ Garden Overview")
        if not beds:
            st.info("Add at least one bed to see the garden overview.")
        else:
            # Visual representation of all beds as a grid of cards
            for bed in beds:
                plants_in_bed_list = bed.get("plants", [])
                sq_ft = bed["width"] * bed["length"]

                # Build companion analysis
                companion_warnings = []
                companion_good = []
                for i, p1 in enumerate(plants_in_bed_list):
                    for p2 in plants_in_bed_list[i + 1:]:
                        rel = companion_relationship(p1, p2, companion_data)
                        if rel == "bad":
                            companion_warnings.append(f"⚠️ {p1} & {p2} are poor companions")
                        elif rel == "good":
                            companion_good.append(f"✅ {p1} & {p2} are great companions")

                # Plotly figure for this bed
                fig = go.Figure()

                # Draw bed outline
                fig.add_shape(
                    type="rect",
                    x0=0, y0=0,
                    x1=bed["width"], y1=bed["length"],
                    line=dict(color="#5D4037", width=3),
                    fillcolor="#8D6E63",
                    opacity=0.15,
                )

                # Place plant circles
                if plants_in_bed_list:
                    n = len(plants_in_bed_list)
                    cols_grid = max(1, math.ceil(math.sqrt(n * bed["width"] / bed["length"])))
                    rows_grid = math.ceil(n / cols_grid)
                    cell_w = bed["width"] / cols_grid
                    cell_h = bed["length"] / rows_grid

                    for idx, plant in enumerate(plants_in_bed_list):
                        row = idx // cols_grid
                        col = idx % cols_grid
                        cx = cell_w * col + cell_w / 2
                        cy = cell_h * row + cell_h / 2
                        color = get_plant_color(plant, companion_data)
                        spacing = get_spacing(plant, companion_data)
                        count = plants_in_bed(cell_w, cell_h, spacing["spacing_in"])

                        fig.add_shape(
                            type="circle",
                            x0=cx - cell_w * 0.35, y0=cy - cell_h * 0.35,
                            x1=cx + cell_w * 0.35, y1=cy + cell_h * 0.35,
                            fillcolor=color,
                            line_color=color,
                            opacity=0.6,
                        )
                        fig.add_annotation(
                            x=cx, y=cy,
                            text=f"<b>{plant[:12]}</b><br>~{count} plants",
                            showarrow=False,
                            font=dict(size=10, color="white"),
                            align="center",
                        )

                sun_color = {"Full Sun (6+ hrs)": "#FFF176", "Part Sun (3-6 hrs)": "#FFE082", "Shade (<3 hrs)": "#B0BEC5"}.get(bed["sun"], "#E8F5E9")

                fig.update_layout(
                    title=dict(
                        text=f"🛏️ {bed['name']}  |  {bed['width']}×{bed['length']} ft  |  {sq_ft:.0f} sq ft  |  {bed['sun']}",
                        font=dict(size=13),
                    ),
                    xaxis=dict(range=[-0.3, bed["width"] + 0.3], showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(range=[-0.3, bed["length"] + 0.3], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x"),
                    height=max(250, int(bed["length"] * 60 + 60)),
                    margin=dict(l=10, r=10, t=45, b=10),
                    paper_bgcolor=sun_color,
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

                if companion_good:
                    for msg in companion_good:
                        st.success(msg)
                if companion_warnings:
                    for msg in companion_warnings:
                        st.warning(msg)
                st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SPACING CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_spacing:
    st.subheader("📏 Spacing & Yield Calculator")
    st.caption("Calculate how many plants fit in your space and estimate yields.")

    col_a, col_b = st.columns(2)
    with col_a:
        calc_plant = st.selectbox("Select Plant", plant_list, key="calc_plant")
        calc_width = st.number_input("Bed / Area Width (ft)", min_value=0.5, max_value=50.0, value=4.0, step=0.5, key="calc_w")
        calc_length = st.number_input("Bed / Area Length (ft)", min_value=0.5, max_value=50.0, value=8.0, step=0.5, key="calc_l")

    spacing_info = get_spacing(calc_plant, companion_data)
    spacing_in = spacing_info["spacing_in"]
    row_spacing = spacing_info["row_spacing_in"]
    depth = spacing_info["depth_in"]

    with col_b:
        st.markdown("**Recommended Spacing**")
        st.markdown(f"- Plant spacing: **{spacing_in} inches**")
        st.markdown(f"- Row spacing: **{row_spacing} inches**")
        st.markdown(f"- Planting depth: **{depth} inches**")

        sqft = calc_width * calc_length
        count = plants_in_bed(calc_width, calc_length, spacing_in)
        st.markdown("---")
        st.markdown(f"**Area:** {sqft:.0f} sq ft")
        st.markdown(f"**Estimated Plants:** {count}")

        # Per-square-foot capacity from CSV data
        plant_rows = df[df["Seed"] == calc_plant]
        if "Per Square" in plant_rows.columns:
            per_sq = plant_rows["Per Square"].dropna()
            if not per_sq.empty:
                try:
                    ps_val = float(per_sq.iloc[0])
                    sqft_count = int(ps_val * sqft)
                    st.markdown(f"**Square Foot Method:** {sqft_count} plants ({ps_val}/sq ft)")
                except (ValueError, TypeError):
                    pass

    st.markdown("---")

    # ── Full spacing reference table ──
    st.subheader("📋 Full Spacing Reference")
    spacing_guide = companion_data.get("spacing_guide", {})
    spacing_rows = []
    for plant, info in spacing_guide.items():
        plant_rows = df[df["Seed"] == plant]
        per_sq = ""
        if not plant_rows.empty and "Per Square" in plant_rows.columns:
            ps = plant_rows["Per Square"].dropna()
            if not ps.empty:
                per_sq = ps.iloc[0]
        spacing_rows.append({
            "Plant": plant,
            "Spacing (in)": info["spacing_in"],
            "Row Spacing (in)": info["row_spacing_in"],
            "Depth (in)": info["depth_in"],
            "Per Sq Ft (SFG)": round((12 / info["spacing_in"]) ** 2, 1),
            "Per Sq (CSV)": per_sq,
        })
    spacing_df = pd.DataFrame(spacing_rows).sort_values("Plant")
    st.dataframe(spacing_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SUNLIGHT PLANNER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sunlight:
    st.subheader("☀️ Sunlight Planner")
    st.caption("View your plants grouped by sunlight requirements.")

    sun_groups = df.groupby("Sun")["Display Name"].apply(list).to_dict() if "Sun" in df.columns else {}

    sun_icons = companion_data.get("sun_icons", {})

    for sun_level, plants in sorted(sun_groups.items()):
        icon = sun_icons.get(sun_level, "🌿")
        with st.expander(f"{icon} {sun_level} ({len(plants)} varieties)", expanded=(sun_level == "Full Sun")):
            # Group by seed family
            families = {}
            for p in plants:
                seed = p.split(" ")[0]
                families.setdefault(seed, []).append(p)

            cols = st.columns(min(4, len(families)))
            for i, (seed, variants) in enumerate(sorted(families.items())):
                color = get_plant_color(seed, companion_data)
                with cols[i % len(cols)]:
                    st.markdown(
                        f'<div style="background:{color}22; border-left:4px solid {color}; '
                        f'padding:8px; border-radius:4px; margin-bottom:6px;">'
                        f"<b>{seed}</b><br><small>{'<br>'.join(variants)}</small></div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.subheader("🗺️ Sunlight Zone Map")
    st.info(
        "💡 **Tip:** Arrange tall plants (Corn, Tomato, Zucchini) on the north side of your garden "
        "so they don't shade shorter plants. Use shade-tolerant varieties under trellises."
    )

    # Sunlight allocation chart
    if "Sun" in df.columns:
        sun_counts = df["Sun"].value_counts().reset_index()
        sun_counts.columns = ["Sun Level", "Count"]
        sun_color_map = {
            "Full Sun": "#FFD54F",
            "Part Sun": "#FFB74D",
            "Part to Full": "#FFF176",
            "Shade": "#90A4AE",
        }
        fig_sun = go.Figure(
            go.Bar(
                x=sun_counts["Sun Level"],
                y=sun_counts["Count"],
                marker_color=[sun_color_map.get(s, "#81C784") for s in sun_counts["Sun Level"]],
                text=sun_counts["Count"],
                textposition="outside",
            )
        )
        fig_sun.update_layout(
            xaxis_title="",
            yaxis_title="Number of Varieties",
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sun, use_container_width=True)