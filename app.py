"""
Verti Garden Planner — Home Dashboard
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.helpers import (
    load_companion_data,
    load_harvest_log,
    load_seeds_df,
    setup_page,
    sidebar_nav,
)

setup_page("Home", "🌿")
sidebar_nav()

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="verti-header">
        <span style="font-size:2rem;">🌿</span>
        <div>
            <h1 style="margin:0; font-size:1.8rem; color:#2C3E2D;">Verti Garden Planner</h1>
            <p style="margin:0; color:#5a7a5b; font-size:0.95rem;">
                Your complete growing season companion
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ─── Load data ────────────────────────────────────────────────────────────────
df = load_seeds_df()
harvest_df = load_harvest_log()
companion_data = load_companion_data()

today = datetime.date.today()
growing_season_end = datetime.date(today.year, 10, 13)

# ─── Summary Metrics ──────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

total_plants = len(df)
warm_plants = len(df[df["Season"] == "Warm"]) if "Season" in df.columns else 0
cool_plants = len(df[df["Season"] == "Cool"]) if "Season" in df.columns else 0
perennials = len(df[df["Season"] == "Perennial"]) if "Season" in df.columns else 0

col1.metric("🌱 Total Varieties", total_plants)
col2.metric("☀️ Warm Season", warm_plants)
col3.metric("❄️ Cool Season", cool_plants)
col4.metric("🌿 Perennials", perennials)

st.markdown("---")

# ─── Two-column layout ────────────────────────────────────────────────────────
left, right = st.columns([2, 1])

with left:
    st.subheader("📅 What to Do This Week")

    # Events within next 14 days
    upcoming = []
    for _, row in df.iterrows():
        start = row["Start Date"]
        end = row["End Date"]
        name = row["Display Name"]
        method = row.get("Planting Method", "")

        if pd.notna(start):
            days_to_start = (start.date() - today).days
            if 0 <= days_to_start <= 14:
                upcoming.append(
                    {"Days": days_to_start, "Action": "Start Indoors / Sow", "Plant": name, "Method": method}
                )
            elif -3 <= days_to_start < 0:
                upcoming.append(
                    {"Days": days_to_start, "Action": "⚠️ Overdue — Start Indoors", "Plant": name, "Method": method}
                )

        if pd.notna(end):
            days_to_end = (end.date() - today).days
            if 0 <= days_to_end <= 14:
                upcoming.append(
                    {"Days": days_to_end, "Action": "Transplant / Direct Sow", "Plant": name, "Method": method}
                )
            elif -3 <= days_to_end < 0:
                upcoming.append(
                    {"Days": days_to_end, "Action": "⚠️ Overdue — Transplant", "Plant": name, "Method": method}
                )

    if upcoming:
        upcoming_df = (
            pd.DataFrame(upcoming).sort_values("Days").reset_index(drop=True)
        )
        upcoming_df["Days Label"] = upcoming_df["Days"].apply(
            lambda d: "Today" if d == 0 else (f"In {d} days" if d > 0 else f"{abs(d)} days ago")
        )
        st.dataframe(
            upcoming_df[["Days Label", "Action", "Plant", "Method"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("🎉 No tasks in the next 14 days. Enjoy your garden!")

    st.markdown("---")

    # ── Mini planting timeline (current ±3 weeks) ──
    st.subheader("🗓️ Upcoming Schedule (Next 6 Weeks)")
    window_start = pd.Timestamp(today)
    window_end = pd.Timestamp(today + datetime.timedelta(weeks=6))
    mask = (
        (df["Start Date"] <= window_end) & (df["End Date"] >= window_start)
        | (df["Start Date"] >= window_start) & (df["Start Date"] <= window_end)
    )
    df_window = df[mask].copy()
    if not df_window.empty:
        ordered = (
            df_window.groupby("Display Name")["Start Date"]
            .min()
            .sort_values()
            .index.tolist()
        )
        fig = px.timeline(
            df_window,
            x_start="Start Date",
            x_end="End Date",
            y="Display Name",
            color="Planting Method",
            color_discrete_map={
                "Transplant": "#4CAF50",
                "Direct Sow": "#FF9800",
            },
            category_orders={"Display Name": ordered},
            labels={"Display Name": "Plant"},
        )
        fig.add_vline(x=str(today), line_dash="dot", line_color="red", line_width=2)
        fig.update_layout(
            height=max(300, 35 * len(df_window["Display Name"].unique())),
            margin=dict(l=160, r=10, t=20, b=20),
            legend_title_text="Method",
            xaxis_title="",
            yaxis_title="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_xaxes(range=[str(window_start.date()), str(window_end.date())])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No planting events in the next 6 weeks.")

with right:
    st.subheader("🌡️ Season Overview")

    # Season breakdown donut
    if "Season" in df.columns:
        season_counts = df["Season"].value_counts().reset_index()
        season_counts.columns = ["Season", "Count"]
        fig_donut = px.pie(
            season_counts,
            names="Season",
            values="Count",
            hole=0.5,
            color="Season",
            color_discrete_map={
                "Warm": "#FF9800",
                "Cool": "#42A5F5",
                "Perennial": "#66BB6A",
            },
        )
        fig_donut.update_layout(
            showlegend=True,
            margin=dict(l=0, r=0, t=10, b=0),
            height=220,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")
    st.subheader("🌿 Planting Method Split")

    if "Planting Method" in df.columns:
        method_counts = df["Planting Method"].value_counts().reset_index()
        method_counts.columns = ["Method", "Count"]
        fig_bar = px.bar(
            method_counts,
            x="Method",
            y="Count",
            color="Method",
            color_discrete_map={
                "Transplant": "#4CAF50",
                "Direct Sow": "#FF9800",
            },
            text="Count",
        )
        fig_bar.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            height=200,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="",
            yaxis_title="",
        )
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("📦 Brands in Collection")

    if "Brand" in df.columns:
        brand_counts = df["Brand"].value_counts().head(6)
        for brand, cnt in brand_counts.items():
            pct = int(cnt / len(df) * 100)
            st.markdown(
                f"**{brand}** — {cnt} varieties  \n"
                f'<div style="background:#e8f5e9;border-radius:4px;height:8px;">'
                f'<div style="background:#4CAF50;width:{pct}%;height:8px;border-radius:4px;"></div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

# ─── Footer navigation cards ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("🗺️ Navigate to")
c1, c2, c3, c4, c5 = st.columns(5)

card_style = (
    "border:1px solid #C8E6C9; border-radius:10px; padding:16px; "
    "text-align:center; background:#fff; cursor:pointer;"
)

c1.markdown(
    f'<div style="{card_style}"><div style="font-size:2rem;">🗓️</div>'
    "<b>Planting Schedule</b><br><small>Full timeline view</small></div>",
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div style="{card_style}"><div style="font-size:2rem;">🌿</div>'
    "<b>Garden Planner</b><br><small>Visual bed designer</small></div>",
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div style="{card_style}"><div style="font-size:2rem;">📊</div>'
    "<b>Database Manager</b><br><small>Edit seed data</small></div>",
    unsafe_allow_html=True,
)
c4.markdown(
    f'<div style="{card_style}"><div style="font-size:2rem;">🤝</div>'
    "<b>Companion Plants</b><br><small>Planting synergies</small></div>",
    unsafe_allow_html=True,
)
c5.markdown(
    f'<div style="{card_style}"><div style="font-size:2rem;">📈</div>'
    "<b>Analytics</b><br><small>Harvest & insights</small></div>",
    unsafe_allow_html=True,
)
