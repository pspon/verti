"""Plotly figure builders rendered to standalone HTML fragments.

The first chart on a page includes plotly.js from the CDN; pass
``include_js=False`` for subsequent charts so the library loads only once.
"""

from __future__ import annotations

import datetime
import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from verti.logic import get_plant_color, get_spacing, plants_in_bed
from web.views import METHOD_COLORS, SEASON_COLORS

_TRANSPARENT = "rgba(0,0,0,0)"
_SUN_BG = {
    "Full Sun (6+ hrs)": "#FFF176",
    "Part Sun (3-6 hrs)": "#FFE082",
    "Shade (<3 hrs)": "#B0BEC5",
}


def _to_html(fig, include_js: bool) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if include_js else False,
        config={"displayModeBar": False, "responsive": True},
    )


def empty(msg: str) -> str:
    return f'<div class="text-sm text-gray-500 italic py-8 text-center">{msg}</div>'


def timeline(df: pd.DataFrame, today: datetime.date, weeks: int | None = 6,
             include_js: bool = True) -> str:
    if df is None or df.empty:
        return empty("No planting events in this window.")
    ordered = df.groupby("Display Name")["Start Date"].min().sort_values().index.tolist()
    fig = px.timeline(
        df, x_start="Start Date", x_end="End Date", y="Display Name",
        color="Planting Method", color_discrete_map=METHOD_COLORS,
        category_orders={"Display Name": ordered}, labels={"Display Name": "Plant"},
    )
    fig.add_vline(x=str(today), line_dash="dot", line_color="red", line_width=2)
    fig.update_layout(
        height=max(300, 32 * len(ordered)),
        margin=dict(l=10, r=10, t=20, b=20),
        legend_title_text="Method", xaxis_title="", yaxis_title="",
        paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT,
    )
    if weeks:
        ws = pd.Timestamp(today)
        we = pd.Timestamp(today + datetime.timedelta(weeks=weeks))
        fig.update_xaxes(range=[str(ws.date()), str(we.date())])
    return _to_html(fig, include_js)


def season_donut(season_counts: dict, include_js: bool = True) -> str:
    if not season_counts:
        return empty("No season data.")
    data = pd.DataFrame({"Season": list(season_counts), "Count": list(season_counts.values())})
    fig = px.pie(data, names="Season", values="Count", hole=0.5,
                 color="Season", color_discrete_map=SEASON_COLORS)
    fig.update_layout(showlegend=True, margin=dict(l=0, r=0, t=10, b=0),
                      height=240, paper_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)


def method_bar(method_counts: dict, include_js: bool = True) -> str:
    if not method_counts:
        return empty("No method data.")
    data = pd.DataFrame({"Method": list(method_counts), "Count": list(method_counts.values())})
    fig = px.bar(data, x="Method", y="Count", color="Method",
                 color_discrete_map=METHOD_COLORS, text="Count")
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=220,
                      paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT,
                      xaxis_title="", yaxis_title="")
    return _to_html(fig, include_js)


# ─── Garden planner ─────────────────────────────────────────────────────────
def bed_layout(bed: dict, companion_data: dict, include_js: bool = True) -> str:
    """Top-down schematic of a bed with plant circles + capacity labels."""
    width, length = float(bed["width"]), float(bed["length"])
    plants = bed.get("plants", [])
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=width, y1=length,
                  line=dict(color="#5D4037", width=3), fillcolor="#8D6E63", opacity=0.15)

    if plants:
        n = len(plants)
        cols = max(1, math.ceil(math.sqrt(n * width / length)))
        rows = math.ceil(n / cols)
        cell_w, cell_h = width / cols, length / rows
        for idx, plant in enumerate(plants):
            cx = cell_w * (idx % cols) + cell_w / 2
            cy = cell_h * (idx // cols) + cell_h / 2
            color = get_plant_color(plant, companion_data)
            count = plants_in_bed(cell_w, cell_h, get_spacing(plant, companion_data)["spacing_in"])
            fig.add_shape(type="circle", x0=cx - cell_w * 0.35, y0=cy - cell_h * 0.35,
                          x1=cx + cell_w * 0.35, y1=cy + cell_h * 0.35,
                          fillcolor=color, line_color=color, opacity=0.6)
            fig.add_annotation(x=cx, y=cy, text=f"<b>{plant[:12]}</b><br>~{count} plants",
                               showarrow=False, font=dict(size=10, color="white"), align="center")

    fig.update_layout(
        xaxis=dict(range=[-0.3, width + 0.3], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-0.3, length + 0.3], showgrid=False, zeroline=False,
                   showticklabels=False, scaleanchor="x"),
        height=max(240, int(length * 55 + 50)), margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=_SUN_BG.get(bed.get("sun", ""), "#E8F5E9"), plot_bgcolor=_TRANSPARENT,
    )
    return _to_html(fig, include_js)


def sunlight_bar(sun_counts: dict, include_js: bool = True) -> str:
    if not sun_counts:
        return empty("No sun data.")
    color_map = {"Full Sun": "#FFD54F", "Part Sun": "#FFB74D",
                 "Part to Full": "#FFF176", "Shade": "#90A4AE"}
    keys = list(sun_counts)
    fig = go.Figure(go.Bar(
        x=keys, y=list(sun_counts.values()),
        marker_color=[color_map.get(k, "#81C784") for k in keys],
        text=list(sun_counts.values()), textposition="outside",
    ))
    fig.update_layout(xaxis_title="", yaxis_title="Varieties", height=300,
                      margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor=_TRANSPARENT,
                      plot_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)


# ─── Companion matrix ───────────────────────────────────────────────────────
def companion_matrix(z_values, labels, hover, include_js: bool = True) -> str:
    fig = go.Figure(go.Heatmap(
        z=z_values, x=labels, y=labels, text=hover, hoverinfo="text",
        colorscale=[[0.0, "#ffcdd2"], [0.5, "#f5f5f5"], [1.0, "#c8e6c9"]],
        zmin=-1, zmax=1, showscale=False, xgap=2, ygap=2,
    ))
    fig.update_layout(height=max(400, 30 * len(labels) + 100),
                      margin=dict(l=120, r=20, t=20, b=120),
                      xaxis=dict(tickangle=-45, tickfont=dict(size=11)),
                      yaxis=dict(tickfont=dict(size=11)),
                      paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)


# ─── Analytics ──────────────────────────────────────────────────────────────
def harvest_bar(plant_totals: pd.DataFrame, companion_data: dict, include_js: bool = True) -> str:
    if plant_totals.empty:
        return empty("No harvest data.")
    colors = [get_plant_color(p, companion_data) for p in plant_totals["Plant"]]
    fig = go.Figure(go.Bar(
        x=plant_totals["Plant"], y=plant_totals["Total (kg)"], marker_color=colors,
        text=plant_totals["Total (kg)"].apply(lambda x: f"{x:.2f} kg"), textposition="outside",
    ))
    fig.update_layout(xaxis_title="", yaxis_title="Harvest (kg)", height=340,
                      margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor=_TRANSPARENT,
                      plot_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)


def harvest_line(daily: pd.DataFrame, companion_data: dict, include_js: bool = True) -> str:
    if daily.empty:
        return empty("Not enough data for a trend.")
    cmap = {p: get_plant_color(p, companion_data) for p in daily["Plant"].unique()}
    fig = px.line(daily, x="Date", y="Quantity_kg", color="Plant", markers=True,
                  labels={"Quantity_kg": "Harvest (kg)", "Date": ""}, color_discrete_map=cmap)
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor=_TRANSPARENT,
                      plot_bgcolor=_TRANSPARENT, legend_title_text="Plant")
    return _to_html(fig, include_js)


def monthly_activity(merged: pd.DataFrame, include_js: bool = True) -> str:
    if merged.empty:
        return empty("No planting activity data.")
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Start Indoors / Direct Sow", x=merged["Month Label"],
                         y=merged["Starts"], marker_color="#4CAF50"))
    fig.add_trace(go.Bar(name="Transplant / Final Sow", x=merged["Month Label"],
                         y=merged["Transplants"], marker_color="#FF9800"))
    fig.update_layout(barmode="group", height=300, margin=dict(l=0, r=0, t=20, b=0),
                      paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT,
                      xaxis_title="", yaxis_title="Plants", legend_title_text="Activity")
    return _to_html(fig, include_js)


def days_histogram(days_numeric: pd.Series, include_js: bool = True) -> str:
    if days_numeric.empty:
        return empty("Days to harvest data not available.")
    fig = px.histogram(days_numeric, nbins=15,
                       labels={"value": "Days to Harvest", "count": "# Plants"},
                       color_discrete_sequence=["#4CAF50"])
    fig.update_traces(marker_line_width=1, marker_line_color="white")
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor=_TRANSPARENT,
                      plot_bgcolor=_TRANSPARENT, showlegend=False)
    return _to_html(fig, include_js)


def frost_pie(frost_counts: dict, include_js: bool = True) -> str:
    if not frost_counts:
        return empty("No frost data.")
    data = pd.DataFrame({"Tolerance": list(frost_counts), "Count": list(frost_counts.values())})
    cmap = {"Tolerant": "#42A5F5", "Semi-tolerant": "#FFA726", "Not tolerant": "#EF5350"}
    fig = px.pie(data, names="Tolerance", values="Count", color="Tolerance",
                 color_discrete_map=cmap, hole=0.4)
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)


def value_bar(cost_df: pd.DataFrame, companion_data: dict, include_js: bool = True) -> str:
    if cost_df.empty:
        return empty("No value data.")
    colors = [get_plant_color(p, companion_data) for p in cost_df["Plant"]]
    fig = go.Figure(go.Bar(
        x=cost_df["Plant"], y=cost_df["Value ($)"], marker_color=colors,
        text=cost_df["Value ($)"].apply(lambda x: f"${x:.2f}"), textposition="outside",
    ))
    fig.update_layout(xaxis_title="", yaxis_title="Value ($)", height=320,
                      margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor=_TRANSPARENT,
                      plot_bgcolor=_TRANSPARENT)
    return _to_html(fig, include_js)
