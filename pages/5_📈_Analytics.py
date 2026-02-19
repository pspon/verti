"""
Page 5 — Analytics
Harvest tracking, cost analysis, and garden insights.
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
    get_plant_color,
    load_companion_data,
    load_harvest_log,
    load_seeds_df,
    load_planting_rules,
    save_harvest_log,
    setup_page,
    sidebar_nav,
)

setup_page("Analytics", "📈")
sidebar_nav()

st.title("📈 Analytics & Harvest Tracker")
st.caption("Track your harvests, analyze yields, and get insights about your garden.")

year = 2025  # Default year
df = load_seeds_df(year)
harvest_df = load_harvest_log()
companion_data = load_companion_data()
rules = load_planting_rules()

plant_list = sorted(df["Seed"].unique())
variant_list = sorted(df["Display Name"].unique())

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_harvest, tab_insights, tab_companion, tab_cost = st.tabs(
    ["🌾 Harvest Tracker", "📊 Garden Insights", "🤝 Companion Effectiveness", "💰 Cost Analysis"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HARVEST TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_harvest:
    st.subheader("🌾 Log a Harvest")

    with st.form("harvest_form"):
        hc1, hc2, hc3 = st.columns(3)
        with hc1:
            h_date = st.date_input("Harvest Date", value=datetime.date.today())
            h_plant = st.selectbox("Plant (family)", plant_list)
        with hc2:
            # Filter variants for selected plant
            plant_variants = sorted(
                df[df["Seed"] == h_plant]["Display Name"].unique()
            ) if h_plant else variant_list
            h_variant = st.selectbox("Variant", plant_variants)
            h_qty = st.number_input("Quantity (kg)", min_value=0.01, max_value=500.0, value=0.5, step=0.1)
        with hc3:
            h_notes = st.text_area("Notes", placeholder="Quality, conditions, observations...", height=90)

        log_submitted = st.form_submit_button("➕ Log Harvest", type="primary")

        if log_submitted:
            new_entry = pd.DataFrame([{
                "Date": pd.Timestamp(h_date),
                "Plant": h_plant,
                "Variant": h_variant,
                "Quantity_kg": h_qty,
                "Notes": h_notes,
            }])
            updated = pd.concat([harvest_df, new_entry], ignore_index=True)
            save_harvest_log(updated, year)
            harvest_df = updated
            st.success(f"✅ Logged {h_qty} kg of **{h_variant}** on {h_date.strftime('%b %d, %Y')}")
            st.rerun()

    st.markdown("---")

    if harvest_df.empty:
        st.info(
            "🌱 No harvests logged yet. Use the form above to start tracking your yields!"
        )
    else:
        # ── Harvest Summary ──
        total_kg = harvest_df["Quantity_kg"].sum()
        total_entries = len(harvest_df)
        unique_plants = harvest_df["Plant"].nunique()

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("🌾 Total Harvest", f"{total_kg:.2f} kg")
        mc2.metric("📝 Log Entries", total_entries)
        mc3.metric("🌱 Unique Plants", unique_plants)

        st.markdown("---")

        # ── Harvest Log Table ──
        st.subheader("📋 Harvest Log")

        # Filters
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_plant = st.multiselect(
                "Filter by plant", sorted(harvest_df["Plant"].unique()),
                default=sorted(harvest_df["Plant"].unique()),
            )
        with fc2:
            if not harvest_df["Date"].isna().all():
                date_min = harvest_df["Date"].min().date()
                date_max = harvest_df["Date"].max().date()
                date_range = st.date_input(
                    "Date range",
                    value=(date_min, date_max),
                    min_value=date_min,
                    max_value=date_max,
                )
            else:
                date_range = None

        h_display = harvest_df[harvest_df["Plant"].isin(filter_plant)].copy()
        if date_range and len(date_range) == 2:
            h_display = h_display[
                (h_display["Date"].dt.date >= date_range[0])
                & (h_display["Date"].dt.date <= date_range[1])
            ]

        h_display_sorted = h_display.sort_values("Date", ascending=False)
        st.dataframe(
            h_display_sorted,
            width='stretch',
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="MMM D, YYYY"),
                "Quantity_kg": st.column_config.NumberColumn("Qty (kg)", format="%.2f"),
            },
        )

        # ── Delete entry ──
        with st.expander("🗑️ Delete a harvest entry"):
            h_display_sorted["_idx_label"] = (
                h_display_sorted["Date"].dt.strftime("%b %d, %Y")
                + " — "
                + h_display_sorted["Variant"].astype(str)
                + " ("
                + h_display_sorted["Quantity_kg"].astype(str)
                + " kg)"
            )
            del_options = h_display_sorted["_idx_label"].tolist()
            if del_options:
                del_choice = st.selectbox("Select entry to delete", del_options)
                if st.button("🗑️ Delete Entry", type="secondary"):
                    del_idx = h_display_sorted[h_display_sorted["_idx_label"] == del_choice].index[0]
                    updated = harvest_df.drop(index=del_idx).reset_index(drop=True)
                    save_harvest_log(updated, year)
                    st.success("Entry deleted.")
                    st.rerun()

        # ── Harvest chart ──
        st.markdown("---")
        st.subheader("📊 Harvest by Plant")
        plant_totals = (
            h_display.groupby("Plant")["Quantity_kg"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        plant_totals.columns = ["Plant", "Total (kg)"]
        colors = [get_plant_color(p, companion_data) for p in plant_totals["Plant"]]

        fig_bar = go.Figure(
            go.Bar(
                x=plant_totals["Plant"],
                y=plant_totals["Total (kg)"],
                marker_color=colors,
                text=plant_totals["Total (kg)"].apply(lambda x: f"{x:.2f} kg"),
                textposition="outside",
            )
        )
        fig_bar.update_layout(
            xaxis_title="",
            yaxis_title="Harvest (kg)",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Harvest over time ──
        if len(h_display) > 1:
            st.subheader("📅 Harvest Over Time")
            daily = (
                h_display.groupby(["Date", "Plant"])["Quantity_kg"]
                .sum()
                .reset_index()
            )
            fig_line = px.line(
                daily,
                x="Date",
                y="Quantity_kg",
                color="Plant",
                markers=True,
                labels={"Quantity_kg": "Harvest (kg)", "Date": ""},
                color_discrete_map={p: get_plant_color(p, companion_data) for p in daily["Plant"].unique()},
            )
            fig_line.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title_text="Plant",
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # Export harvest log
        st.download_button(
            "⬇️ Export Harvest Log (CSV)",
            data=harvest_df.to_csv(index=False),
            file_name=f"harvest_log_{datetime.date.today()}.csv",
            mime="text/csv",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GARDEN INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_insights:
    st.subheader("📊 Garden Insights")

    # ── Planting timeline density ──
    st.markdown("#### 📅 Planting Activity by Month")
    df_activity = df.copy()
    df_activity["Start Month"] = df_activity["Start Date"].dt.month
    df_activity["End Month"] = df_activity["End Date"].dt.month

    month_labels = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    monthly_counts = (
        df_activity["Start Month"]
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .reset_index()
    )
    monthly_counts.columns = ["Month", "Starts"]
    monthly_counts["Month Label"] = monthly_counts["Month"].map(month_labels)

    monthly_ends = (
        df_activity["End Month"]
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .reset_index()
    )
    monthly_ends.columns = ["Month", "Transplants"]
    monthly_ends["Month Label"] = monthly_ends["Month"].map(month_labels)

    merged = pd.merge(monthly_counts, monthly_ends, on=["Month", "Month Label"], how="outer").fillna(0)
    merged = merged.sort_values("Month")

    fig_activity = go.Figure()
    fig_activity.add_trace(
        go.Bar(name="Start Indoors / Direct Sow", x=merged["Month Label"], y=merged["Starts"],
               marker_color="#4CAF50")
    )
    fig_activity.add_trace(
        go.Bar(name="Transplant / Final Sow", x=merged["Month Label"], y=merged["Transplants"],
               marker_color="#FF9800")
    )
    fig_activity.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="Number of Plants",
        legend_title_text="Activity",
    )
    st.plotly_chart(fig_activity, use_container_width=True)

    # ── Days to harvest distribution ──
    st.markdown("#### ⏱️ Days to Harvest Distribution")
    days_data = df["Days"].dropna()
    try:
        days_numeric = pd.to_numeric(days_data, errors="coerce").dropna()
        if not days_numeric.empty:
            fig_hist = px.histogram(
                days_numeric,
                nbins=15,
                labels={"value": "Days to Harvest", "count": "# Plants"},
                color_discrete_sequence=["#4CAF50"],
            )
            fig_hist.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            fig_hist.update_traces(marker_line_width=1, marker_line_color="white")
            st.plotly_chart(fig_hist, use_container_width=True)
            col_d1, col_d2, col_d3 = st.columns(3)
            col_d1.metric("Fastest", f"{int(days_numeric.min())} days")
            col_d2.metric("Average", f"{int(days_numeric.mean())} days")
            col_d3.metric("Slowest", f"{int(days_numeric.max())} days")
    except Exception:
        st.info("Days to harvest data not available.")

    # ── Brand breakdown ──
    st.markdown("---")
    st.markdown("#### 🏷️ Seed Brand Breakdown")
    if "Brand" in df.columns:
        brand_df = df.groupby("Brand").agg(
            Varieties=("Seed", "count"),
            Plants=("Display Name", "nunique"),
        ).reset_index().sort_values("Varieties", ascending=False)

        fig_brand = px.treemap(
            brand_df,
            path=["Brand"],
            values="Varieties",
            color="Varieties",
            color_continuous_scale="Greens",
            hover_data=["Plants"],
        )
        fig_brand.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_brand, use_container_width=True)

    # ── Frost tolerance ──
    st.markdown("---")
    st.markdown("#### 🌡️ Frost Tolerance Overview")
    if "Frost" in df.columns:
        frost_df = df["Frost"].value_counts().reset_index()
        frost_df.columns = ["Tolerance", "Count"]
        frost_color_map = {
            "Tolerant": "#42A5F5",
            "Semi-tolerant": "#FFA726",
            "Not tolerant": "#EF5350",
        }
        fig_frost = px.pie(
            frost_df,
            names="Tolerance",
            values="Count",
            color="Tolerance",
            color_discrete_map=frost_color_map,
            hole=0.4,
        )
        fig_frost.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_frost, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPANION EFFECTIVENESS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_companion:
    st.subheader("🤝 Companion Effectiveness")
    st.caption("Analyze how companion planting affects yields and growth.")
    rules = load_planting_rules()

    if not rules.get("planting_rules"):
        st.info("No planting rules configured yet. Go to Database Manager → Garden Beds to set up planting rules.")
    else:
        # Show planting rules
        st.dataframe(pd.DataFrame(rules["planting_rules"]).T, use_container_width=True, hide_index=True)

        # Analyze companion effectiveness
        st.subheader("📊 Companion Impact on Yields")
        if not harvest_df.empty:
            # This would require more complex analysis - for now just show harvest data
            st.dataframe(harvest_df, use_container_width=True, hide_index=True)
        else:
            st.info("Log harvests to analyze companion planting effectiveness.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COST ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_cost:
    st.subheader("💰 Cost Analysis")
    st.caption("Estimate the value of growing your own produce vs. buying from a store.")

    st.info(
        "💡 Enter approximate seed costs and current market prices to compare "
        "the value of your homegrown produce."
    )

    # ── Market price database ──
    default_prices = {
        "Tomato": 3.50, "Basil": 2.00, "Carrot": 1.50, "Lettuce": 2.50,
        "Radish": 1.80, "Cucumber": 1.80, "Beet": 2.00, "Spinach": 3.00,
        "Corn": 0.80, "Zucchini": 1.50, "Eggplant": 2.50, "Bokchoy": 2.00,
        "Snap Peas": 4.00, "Snow Peas": 4.00, "Ground Cherry": 6.00,
        "Parsnip": 2.50, "Green Onion": 2.00, "Parsley": 2.50, "Sage": 3.00,
        "Dill": 2.00, "Borage": 3.00, "Nasturtium": 2.50, "Shiso": 4.00,
    }

    st.markdown("#### 🏷️ Market Prices ($/kg)")
    st.caption("Adjust these prices to match your local market.")

    # Build editable price table from plants in CSV
    price_data = []
    for plant in plant_list:
        default_price = default_prices.get(plant, 2.00)
        price_data.append({"Plant": plant, "Market Price ($/kg)": default_price})

    price_df = pd.DataFrame(price_data)
    edited_prices = st.data_editor(
        price_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Market Price ($/kg)": st.column_config.NumberColumn(
                "Market Price ($/kg)", min_value=0.0, max_value=100.0, step=0.10, format="$%.2f"
            )
        },
    )

    st.markdown("---")
    st.markdown("#### 🌱 Seed Cost Estimator")

    seed_cost_total = st.number_input(
        "Total seed investment ($)",
        min_value=0.0,
        max_value=10000.0,
        value=150.0,
        step=5.0,
        help="Estimate of what you spent on seeds this season",
    )
    supplies_cost = st.number_input(
        "Supplies / soil / fertilizer ($)",
        min_value=0.0,
        max_value=10000.0,
        value=100.0,
        step=10.0,
    )
    total_investment = seed_cost_total + supplies_cost

    st.markdown("---")
    st.markdown("#### 📊 Value Calculation")

    if harvest_df.empty:
        st.info(
            "Log harvests in the **Harvest Tracker** tab to see your ROI calculation. "
            "Showing example projection below."
        )
        # Build an example projection
        example_data = []
        for plant in plant_list[:8]:
            price_row = edited_prices[edited_prices["Plant"] == plant]
            if not price_row.empty:
                market_price = float(price_row["Market Price ($/kg)"].iloc[0])
                example_qty = 2.0  # 2kg example
                value = example_qty * market_price
                example_data.append({
                    "Plant": plant,
                    "Projected Harvest (kg)": example_qty,
                    "Market Price ($/kg)": market_price,
                    "Estimated Value ($)": round(value, 2),
                })
        if example_data:
            ex_df = pd.DataFrame(example_data)
            st.caption("*Example projection (2kg per plant). Log actual harvests for real calculations.*")
            st.dataframe(ex_df, use_container_width=True, hide_index=True,
                         column_config={"Estimated Value ($)": st.column_config.NumberColumn(format="$%.2f"),
                                        "Market Price ($/kg)": st.column_config.NumberColumn(format="$%.2f")})
    else:
        # Real calculation from harvest log
        harvest_by_plant = (
            harvest_df.groupby("Plant")["Quantity_kg"].sum().reset_index()
        )
        harvest_by_plant.columns = ["Plant", "Harvested (kg)"]

        # Merge with prices
        cost_analysis = pd.merge(harvest_by_plant, edited_prices, on="Plant", how="left")
        cost_analysis["Market Price ($/kg)"] = cost_analysis["Market Price ($/kg)"].fillna(2.0)
        cost_analysis["Value ($)"] = (
            cost_analysis["Harvested (kg)"] * cost_analysis["Market Price ($/kg)"]
        ).round(2)
        total_value = cost_analysis["Value ($)"].sum()
        roi = total_value - total_investment
        roi_pct = (roi / total_investment * 100) if total_investment > 0 else 0

        # Metrics
        rm1, rm2, rm3, rm4 = st.columns(4)
        rm1.metric("💵 Total Investment", f"${total_investment:.2f}")
        rm2.metric("🌾 Harvest Value", f"${total_value:.2f}")
        rm3.metric("📈 ROI", f"${roi:.2f}", delta=f"{roi_pct:+.0f}%")
        rm4.metric("🥦 Total Harvested", f"{harvest_df['Quantity_kg'].sum():.2f} kg")

        st.markdown("---")
        st.dataframe(
            cost_analysis,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Harvested (kg)": st.column_config.NumberColumn(format="%.2f"),
                "Market Price ($/kg)": st.column_config.NumberColumn(format="$%.2f"),
                "Value ($)": st.column_config.NumberColumn(format="$%.2f"),
            },
        )

        # Value breakdown chart
        fig_value = go.Figure(
            go.Bar(
                x=cost_analysis["Plant"],
                y=cost_analysis["Value ($)"],
                marker_color=[get_plant_color(p, companion_data) for p in cost_analysis["Plant"]],
                text=cost_analysis["Value ($)"].apply(lambda x: f"${x:.2f}"),
                textposition="outside",
            )
        )
        fig_value.update_layout(
            xaxis_title="",
            yaxis_title="Estimated Value ($)",
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_value, use_container_width=True)

        # Break-even line
        if roi < 0:
            st.warning(
                f"🎯 You need **${abs(roi):.2f}** more in harvest value to break even. "
                f"Keep growing — the season isn't over yet!"
            )
        else:
            st.success(
                f"🎉 You've exceeded your investment by **${roi:.2f}**! "
                f"Great return on your garden this season."
            )