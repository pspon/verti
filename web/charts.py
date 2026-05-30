"""Plotly figure builders rendered to standalone HTML fragments.

The first chart on a page includes plotly.js from the CDN; pass
``include_js=False`` for subsequent charts so the library loads only once.
"""

from __future__ import annotations

import datetime

import pandas as pd
import plotly.express as px

from web.views import METHOD_COLORS, SEASON_COLORS

_TRANSPARENT = "rgba(0,0,0,0)"


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
