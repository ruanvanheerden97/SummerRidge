"""Branded Plotly charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.branding import BAD, ELEC_COLOR, GAS_COLOR, GREY, NAVY, OK, WARN
from src.master import FLOOR_ORDER

STATUS_COLORS = {"Reporting": OK, "Late": WARN, "Offline": BAD, "No data": GREY}

_LAYOUT = dict(
    font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", color=NAVY),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=48, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)


def _floor_axis(fig: go.Figure) -> None:
    fig.update_xaxes(categoryorder="array", categoryarray=FLOOR_ORDER, title=None)
    fig.update_yaxes(gridcolor="#E3E6E8", title=None)


def installation_by_floor(master: pd.DataFrame, utility: str, title: str) -> go.Figure:
    """Stacked bar per floor: AMR installed vs outstanding."""
    sub = master[master["utility"] == utility]
    grp = sub.groupby("floor")["amr_active"].agg(installed="sum", total="count").reset_index()
    grp["outstanding"] = grp["total"] - grp["installed"]
    color = ELEC_COLOR if utility == "elec" else GAS_COLOR
    fig = go.Figure(
        [
            go.Bar(
                x=grp["floor"], y=grp["installed"], name="AMR installed",
                marker_color=color, text=grp["installed"], textposition="inside",
            ),
            go.Bar(
                x=grp["floor"], y=grp["outstanding"], name="Outstanding",
                marker_color="#D8DDE1", text=grp["outstanding"], textposition="inside",
            ),
        ]
    )
    fig.update_layout(barmode="stack", title=title, **_LAYOUT)
    _floor_axis(fig)
    return fig


def donut(installed: int, total: int, label: str, color: str) -> go.Figure:
    outstanding = total - installed
    fig = go.Figure(
        go.Pie(
            values=[installed, outstanding],
            labels=["AMR installed", "Outstanding"],
            hole=0.62,
            marker=dict(colors=[color, "#D8DDE1"]),
            textinfo="value",
            sort=False,
        )
    )
    pct = (installed / total * 100) if total else 0
    fig.add_annotation(
        text=f"<b>{pct:.0f}%</b><br><span style='font-size:12px'>{label}</span>",
        showarrow=False, font=dict(size=22, color=NAVY),
    )
    fig.update_layout(height=260, showlegend=False, **_LAYOUT)
    return fig


def status_by_floor(merged: pd.DataFrame, title: str) -> go.Figure:
    """Stacked bar per floor of AMR meter health (Reporting/Late/Offline/No data)."""
    fig = go.Figure()
    grp = merged.groupby(["floor", "status"]).size().unstack(fill_value=0)
    for status in ["Reporting", "Late", "Offline", "No data"]:
        if status in grp.columns:
            fig.add_bar(
                x=grp.index, y=grp[status], name=status,
                marker_color=STATUS_COLORS[status],
                text=grp[status].replace(0, ""), textposition="inside",
            )
    fig.update_layout(barmode="stack", title=title, **_LAYOUT)
    _floor_axis(fig)
    return fig


def history_chart(hist: pd.DataFrame, serial: str, utility: str, unit: str) -> go.Figure:
    """Cumulative index line + daily consumption bars for one meter."""
    color = ELEC_COLOR if utility == "elec" else GAS_COLOR
    div = 1000.0 if utility == "gas" else 1.0
    vals = hist["reading_value"] / div

    fig = go.Figure()
    fig.add_scatter(
        x=hist["reading_ts"], y=vals, mode="lines+markers",
        name=f"Meter index ({unit})", line=dict(color=color, width=2.5),
        marker=dict(size=6),
    )
    # consumption between consecutive readings, shown on a secondary axis
    cons = vals.diff()
    fig.add_bar(
        x=hist["reading_ts"], y=cons, name=f"Consumption since previous reading ({unit})",
        marker_color=NAVY, opacity=0.35, yaxis="y2",
    )
    fig.update_layout(
        title=f"Meter {serial} — history",
        yaxis=dict(title=f"Index ({unit})", gridcolor="#E3E6E8"),
        yaxis2=dict(title=f"Consumption ({unit})", overlaying="y", side="right", showgrid=False),
        xaxis=dict(title=None),
        hovermode="x unified",
        **_LAYOUT,
    )
    return fig
