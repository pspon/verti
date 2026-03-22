"""
Page 4 — Companion Planting Guide
Interactive companion plant lookup, compatibility matrix, and planting tips.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import (
    companion_relationship,
    get_plant_color,
    load_companion_data,
    load_seeds_df,
    load_planting_rules,
    setup_page,
    sidebar_nav,
)

setup_page("Companion Plants", "🤝")
sidebar_nav()

st.title("🤝 Companion Planting Guide")
st.caption("Discover which plants grow best together — and which to keep apart.")

year = 2026  # Default year
df = load_seeds_df(year)
companion_data = load_companion_data()
companions = companion_data.get("companions", {})
rules = load_planting_rules()

# All plants in the companion database + CSV
all_plants_companion = sorted(companions.keys())
all_plants_csv = sorted(df["Seed"].unique())
all_plants = sorted(set(all_plants_companion + all_plants_csv))

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_lookup, tab_matrix, tab_tips = st.tabs(
    ["🔍 Plant Lookup", "🗂️ Compatibility Matrix", "💡 Planting Tips"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PLANT LOOKUP
# ═══════════════════════════════════════════════════════════════════════════════
with tab_lookup:
    st.subheader("🔍 Find Companions for a Plant")

    selected_plant = st.selectbox("Choose a plant:", all_plants)
    color = get_plant_color(selected_plant, companion_data)

    # Show plant header card
    plant_info = companions.get(selected_plant, {})
    good_list = plant_info.get("good", [])
    bad_list = plant_info.get("bad", [])
    notes = plant_info.get("notes", "No specific notes available.")

    st.markdown(
        f'<div style="background:{color}22; border-left:5px solid {color}; '
        f'padding:14px 18px; border-radius:8px; margin-bottom:1rem;">'
        f'<h3 style="margin:0; color:{color}">🌱 {selected_plant}</h3>'
        f'<p style="margin:4px 0 0; color:#555;">{notes}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )

    c_good, c_bad = st.columns(2)

    with c_good:
        st.markdown("### ✅ Good Companions")
        if good_list:
            for p in good_list:
                pc = get_plant_color(p, companion_data)
                st.markdown(
                    f'<div style="background:{pc}22; border:1px solid {pc}; '
                    f'border-radius:6px; padding:8px 12px; margin-bottom:6px;">'
                    f'<span style="font-weight:600;">{p}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No specific good companions recorded.")

    with c_bad:
        st.markdown("### ⛔ Poor Companions")
        if bad_list:
            for p in bad_list:
                st.markdown(
                    f'<div style="background:#ffcdd2; border:1px solid #e57373; '
                    f'border-radius:6px; padding:8px 12px; margin-bottom:6px;">'
                    f'<span style="font-weight:600;">{p}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No known bad companions — this plant is very sociable! 🎉")

    # ── Check two plants together ──
    st.markdown("---")
    st.subheader("🔄 Check Two Plants Together")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        plant_a = st.selectbox("Plant A", all_plants, key="pair_a")
    with col_p2:
        plant_b = st.selectbox(
            "Plant B",
            [p for p in all_plants if p != plant_a],
            key="pair_b",
        )

    rel = companion_relationship(plant_a, plant_b, companion_data)
    if rel == "good":
        st.success(f"✅ **{plant_a}** and **{plant_b}** are great companions! Plant them together.")
        # Get the specific note
        info_a = companions.get(plant_a, {})
        if plant_b in info_a.get("good", []):
            st.info(f"💡 {info_a.get('notes', '')}")
    elif rel == "bad":
        st.error(f"⛔ **{plant_a}** and **{plant_b}** are poor companions. Keep them apart.")
        info_a = companions.get(plant_a, {})
        if plant_b in info_a.get("bad", []):
            st.warning(f"💡 {info_a.get('notes', '')}")
    else:
        st.info(f"ℹ️ **{plant_a}** and **{plant_b}** have no known interaction — they should be fine together.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPATIBILITY MATRIX
# ═══════════════════════════════════════════════════════════════════════════════
with tab_matrix:
    st.subheader("🗂️ Companion Planting Matrix")
    st.caption("Green = good companions | Red = poor companions | White = neutral")

    # Let user pick a subset of plants
    matrix_plants = st.multiselect(
        "Select plants for matrix",
        all_plants,
        default=[p for p in all_plants_companion[:16] if p in all_plants],
    )

    if len(matrix_plants) < 2:
        st.warning("Select at least 2 plants to build the matrix.")
    else:
        n = len(matrix_plants)
        z_values = []
        hover_text = []

        for p1 in matrix_plants:
            row_z = []
            row_hover = []
            for p2 in matrix_plants:
                if p1 == p2:
                    row_z.append(0)
                    row_hover.append(f"{p1} (same plant)")
                else:
                    rel = companion_relationship(p1, p2, companion_data)
                    if rel == "good":
                        row_z.append(1)
                        row_hover.append(f"✅ {p1} + {p2}: Good companions")
                    elif rel == "bad":
                        row_z.append(-1)
                        row_hover.append(f"⛔ {p1} + {p2}: Poor companions")
                    else:
                        row_z.append(0)
                        row_hover.append(f"⬜ {p1} + {p2}: Neutral")
                    
            z_values.append(row_z)
            hover_text.append(row_hover)

        fig = go.Figure(
            go.Heatmap(
                z=z_values,
                x=matrix_plants,
                y=matrix_plants,
                text=hover_text,
                hoverinfo="text",
                colorscale=[
                    [0.0, "#ffcdd2"],
                    [0.5, "#f5f5f5"],
                    [1.0, "#c8e6c9"],
                ],
                zmin=-1,
                zmax=1,
                showscale=False,
                xgap=2,
                ygap=2,
            )
        )
        fig.update_layout(
            height=max(400, 30 * n + 100),
            margin=dict(l=120, r=20, t=20, b=120),
            xaxis=dict(tickangle=-45, tickfont=dict(size=11)),
            yaxis=dict(tickfont=dict(size=11)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Legend
        lc1, lc2, lc3 = st.columns(3)
        lc1.markdown('<span class="badge-good">✅ Good Companions</span>', unsafe_allow_html=True)
        lc2.markdown('<span class="badge-bad">⛔ Poor Companions</span>', unsafe_allow_html=True)
        lc3.markdown('<span class="badge-neutral">⬜ Neutral</span>', unsafe_allow_html=True)

        # ── Summary count ──
        good_count = sum(cell for row in z_values for cell in row if cell == 1) // 2
        bad_count = sum(1 for row in z_values for cell in row if cell == -1) // 2
        st.markdown(f"**{good_count} good pairings** · **{bad_count} incompatible pairings** among selected plants")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PLANTING TIPS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_tips:
    st.subheader("💡 General Companion Planting Tips")

    tips = [
        {
            "icon": "🌼",
            "title": "Use Flowers as Pest Deterrents",
            "body": "Plant **Marigolds**, **Nasturtiums**, and **Borage** throughout your garden. "
            "Marigolds repel nematodes and aphids, Nasturtiums act as trap crops for aphids, "
            "and Borage deters tomato hornworm while attracting pollinators.",
        },
        {
            "icon": "🌿",
            "title": "The Three Sisters",
            "body": "**Corn**, **Beans**, and **Squash/Zucchini** are a classic trio. "
            "Corn provides a pole for beans to climb, beans fix nitrogen for corn and squash, "
            "and squash leaves shade the ground to retain moisture and deter weeds.",
        },
        {
            "icon": "🧄",
            "title": "Alliums as Pest Repellents",
            "body": "**Garlic Chives** planted near roses, vegetables, and fruit trees help repel "
            "aphids, Japanese beetles, and fungal diseases. They have natural antifungal properties.",
        },
        {
            "icon": "🍅",
            "title": "Tomato & Basil — The Classic Pair",
            "body": "Basil is one of the best companions for tomatoes. It repels aphids, "
            "whiteflies, and mosquitoes, and many gardeners believe it improves tomato flavor. "
            "Plant basil 12–18 inches from tomatoes for best results.",
        },
        {
            "icon": "🥕",
            "title": "Interplanting Root & Leaf Vegetables",
            "body": "**Carrots** and **Lettuce** make great neighbors — carrots loosen soil "
            "that lettuce benefits from, and lettuce provides ground cover to keep carrot "
            "roots cool. Add **Radishes** as a quick crop and natural pest decoy.",
        },
        {
            "icon": "📐",
            "title": "Spacing Matters",
            "body": "Even beneficial companions need adequate spacing. Overcrowding reduces "
            "airflow and can increase disease risk. Use the **Spacing Calculator** page "
            "to determine exact plant counts for your beds.",
        },
        {
            "icon": "🔄",
            "title": "Rotate Your Crops",
            "body": "Don't plant the same family in the same spot year after year. Rotate: "
            "**nightshades** (Tomato, Eggplant) → **brassicas** (Bokchoy) → "
            "**legumes** (Peas) → **roots** (Carrot, Beet). This breaks pest cycles and "
            "replenishes soil nutrients.",
        },
        {
            "icon": "🌱",
            "title": "Nitrogen Fixers",
            "body": "**Peas** (Snap Peas, Snow Peas) fix atmospheric nitrogen into the soil, "
            "benefiting nearby heavy feeders like **Corn**, **Lettuce**, and **Spinach**. "
            "After peas finish, cut them at ground level and leave roots to decompose.",
        },
    ]

    for tip in tips:
        with st.expander(f"{tip['icon']} {tip['title']}"):
            st.markdown(tip["body"])

    st.markdown("---")
    st.subheader("📋 Quick Reference: Your Garden's Companion Stats")

    # Count good/bad pairings for each plant in the user's CSV
    stats = []
    for plant in all_plants_csv:
        info = companions.get(plant, {})
        good = len(info.get("good", []))
        bad = len(info.get("bad", []))
        in_db = "✅" if plant in companions else "—"
        stats.append({
            "Plant": plant,
            "In Companion DB": in_db,
            "Good Companions": good,
            "Poor Companions": bad,
            "Notes": info.get("notes", ""),
        })
    stats_df = pd.DataFrame(stats).sort_values("Good Companions", ascending=False)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)