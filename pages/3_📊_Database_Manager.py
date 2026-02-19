"""
Page 3 — Database Manager
Interactive CSV editor for seed and planting data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
import io

import pandas as pd
import streamlit as st

from utils.helpers import (
    load_seeds_df,
    reload_seeds,
    load_harvest_log,
    save_harvest_log,
    load_garden_beds,
    save_garden_beds,
    load_planting_rules,
    save_planting_rules,
    load_companion_data,
    setup_page,
    sidebar_nav,
)

setup_page("Database Manager", "📊")
sidebar_nav()

st.title("📊 Database Manager")
st.caption("View, edit, add, and delete your seed and planting data.")

# ─── Load data ────────────────────────────────────────────────────────────────
year = 2025  # Default year
df = load_seeds_df(year)

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_view, tab_harvest, tab_beds, tab_companion = st.tabs(
    ["🔍 View & Search", "🌾 Harvest Log", "🛏️ Garden Beds", "🤝 Companion Plants"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VIEW & SEARCH
# ═══════════════════════════════════════════════════════════════════════════════
with tab_view:
    st.subheader("📋 Seed Database")

    # Quick search
    search = st.text_input("🔍 Search by name, variant, or brand", placeholder="e.g. Tomato, McKenzie, Basil…")

    # Column filter
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        if "Season" in df.columns:
            seasons = ["All"] + sorted(df["Season"].dropna().unique().tolist())
            sel_season = st.selectbox("Season", seasons)
    with col_filter2:
        if "Planting Method" in df.columns:
            methods = ["All"] + sorted(df["Planting Method"].dropna().unique().tolist())
            sel_method = st.selectbox("Planting Method", methods)
    with col_filter3:
        if "Frost" in df.columns:
            frosts = ["All"] + sorted(df["Frost"].dropna().unique().tolist())
            sel_frost = st.selectbox("Frost Tolerance", frosts)

    df_view = df.copy()

    if search:
        mask = (
            df_view["Seed"].astype(str).str.contains(search, case=False, na=False)
            | df_view["Variant"].astype(str).str.contains(search, case=False, na=False)
            | df_view["Brand"].astype(str).str.contains(search, case=False, na=False)
        )
        df_view = df_view[mask]

    if "Season" in df_view.columns and sel_season != "All":
        df_view = df_view[df_view["Season"] == sel_season]
    if "Planting Method" in df_view.columns and sel_method != "All":
        df_view = df_view[df_view["Planting Method"] == sel_method]
    if "Frost" in df_view.columns and sel_frost != "All":
        df_view = df_view[df_view["Frost"] == sel_frost]

    st.markdown(f"**{len(df_view)} records** matching filters")

    # Highlight rows where Plant in 2025 = TRUE
    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Start Indoors": st.column_config.DateColumn("Start Indoors", format="MMM D, YYYY"),
            "Transplant / Sow": st.column_config.DateColumn("Transplant / Sow", format="MMM D, YYYY"),
            "Plant in 2025": st.column_config.CheckboxColumn("Plant in 2025"),
            "Days": st.column_config.NumberColumn("Days to Harvest"),
            "Days (after transplant)": st.column_config.NumberColumn("Days (after transplant)"),
            "Per Square": st.column_config.NumberColumn("Per Sq Ft"),
            "Year": st.column_config.TextColumn("Seed Year"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HARVEST LOG
# ═══════════════════════════════════════════════════════════════════════════════
with tab_harvest:
    st.subheader("🌾 Harvest Log")
    st.caption("Track what you've harvested, when, and how much.")

    # Load harvest log
    harvest_df = load_harvest_log()

    st.dataframe(harvest_df, use_container_width=True, hide_index=True)

    # Add new harvest entry
    with st.form("add_harvest"):
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            harvest_plant = st.selectbox("Plant", df["Display Name"].unique())
        with col_h2:
            harvest_date = st.date_input("Date", value=datetime.date.today())
        with col_h3:
            harvest_qty = st.number_input("Quantity (kg)", min_value=0.0, step=0.1, value=0.5)

        harvest_notes = st.text_input("Notes", placeholder="e.g. First harvest, good yield")

        if st.form_submit_button("➕ Add Harvest", type="primary"):
            new_harvest = pd.DataFrame([{
                "Date": harvest_date,
                "Plant": harvest_plant,
                "Variant": df[df["Display Name"] == harvest_plant]["Variant"].iloc[0],
                "Quantity_kg": harvest_qty,
                "Notes": harvest_notes,
            }])
            harvest_df = pd.concat([harvest_df, new_harvest], ignore_index=True)
            save_harvest_log(harvest_df)
            st.success(f"✅ Added harvest for {harvest_plant}")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GARDEN BEDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_beds:
    st.subheader("🛏️ Garden Beds")
    st.caption("Manage your garden bed layouts and plant assignments.")

    # Load garden beds
    beds = load_garden_beds()
    rules = load_planting_rules()

    col_b1, col_b2 = st.columns(2)

    with col_b1:
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
            df["Display Name"].unique(),
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

    with col_b2:
        st.subheader("Planting Rules")
        st.caption("Configure planting dates and rules for each plant.")

        if st.button("🔄 Load Rules", type="secondary"):
            rules = load_planting_rules()
            st.success("Loaded planting rules")

        # Display rules
        if rules:
            st.dataframe(pd.DataFrame(rules["planting_rules"]).T, use_container_width=True, hide_index=True)

            # Add/edit rule
            with st.form("add_rule"):
                rule_plant = st.selectbox("Plant", df["Display Name"].unique())
                rule_start = st.number_input("Start Indoors Delta (days)", min_value=-60, max_value=60, value=0)
                rule_trans = st.number_input("Transplant Delta (days)", min_value=-60, max_value=60, value=0)
                rule_frost = st.number_input("Last Frost Delta (days)", min_value=-60, max_value=60, value=0)

                if st.form_submit_button("💾 Save Rule", type="primary"):
                    rules["planting_rules"][rule_plant] = {
                        "start_indoors_delta": int(rule_start) if rule_start != 0 else None,
                        "transplant_delta": int(rule_trans) if rule_trans != 0 else None,
                        "last_frost_delta": int(rule_frost) if rule_frost != 0 else None,
                    }
                    save_planting_rules(rules)
                    st.success(f"✅ Saved rule for {rule_plant}")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMPANION PLANTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_companion:
    st.subheader("🤝 Companion Plants")
    st.caption("View and manage companion planting relationships.")
    rules = load_planting_rules()

    st.info("Companion planting rules are managed in the Companion Plants page.")

    # Display companion data
    companion_data = load_companion_data()
    st.dataframe(pd.DataFrame(companion_data["companions"]).T, use_container_width=True, hide_index=True)