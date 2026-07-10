"""Live AMR Readings — latest reading per meter, health status, floor view."""
import pandas as pd
import streamlit as st

from src.branding import BAD, GREY, OK, WARN, is_mobile, metric_row, page_header, utility_label
from src.charts import STATUS_COLORS, status_by_floor
from src.data import add_display_columns, get_import_log, get_latest_readings, get_master
from src.master import FLOOR_ORDER

page_header("Live AMR Readings")

master = get_master()
latest = get_latest_readings()
merged = add_display_columns(latest, master)

# ---------------------------------------------------------------- controls
if is_mobile():
    util_choice = st.radio("Utility", ["Both", "Electricity", "Gas"], horizontal=True, key="live_util")
    floor_choice = st.multiselect("Floor", FLOOR_ORDER, default=[], placeholder="All floors")
    refresh = st.button("Refresh data", width='stretch')
else:
    c1, c2, c3 = st.columns([1.2, 1.5, 0.8])
    util_choice = c1.radio(
        "Utility", ["Both", "Electricity", "Gas"], horizontal=True, key="live_util"
    )
    floor_choice = c2.multiselect("Floor", FLOOR_ORDER, default=[], placeholder="All floors")
    refresh = c3.button("Refresh data", width='stretch')
if refresh:
    st.cache_data.clear()
    st.rerun()

view = merged.copy()
if util_choice == "Electricity":
    view = view[view["utility"] == "elec"]
elif util_choice == "Gas":
    view = view[view["utility"] == "gas"]
if floor_choice:
    view = view[view["floor"].isin(floor_choice)]

# ---------------------------------------------------------------- KPIs
n_rep = int((view["status"] == "Reporting").sum())
n_late = int((view["status"] == "Late").sum())
n_off = int((view["status"] == "Offline").sum())
n_none = int((view["status"] == "No data").sum())
n_batt = int(view["low_battery"].sum())

metric_row(
    [
        ("Reporting (≤26 h)", n_rep),
        ("Late (26–72 h)", n_late),
        ("Offline (>72 h)", n_off),
        ("Never reported", n_none),
        ("Low battery", n_batt),
    ],
    desktop_cols=5,
)

if n_off or n_none or n_batt:
    st.warning(
        f"Attention needed: {n_off} offline, {n_none} never reported, "
        f"{n_batt} low battery. Filter the table below by status to see them."
    )

# ---------------------------------------------------------------- floor visual
st.plotly_chart(
    status_by_floor(view, "AMR meter health per floor"),
    width='stretch',
)

# ---------------------------------------------------------------- table
st.subheader("Latest reading per meter")
status_filter = st.multiselect(
    "Status", ["Reporting", "Late", "Offline", "No data"], default=[],
    placeholder="All statuses",
)
tbl = view.copy()
if status_filter:
    tbl = tbl[tbl["status"].isin(status_filter)]

tbl = tbl.sort_values(["status", "floor", "stand"])
show = pd.DataFrame(
    {
        "Status": tbl["status"],
        "Floor": tbl["floor"],
        "Stand / Unit": tbl["stand"],
        "Utility": tbl["utility"].map(utility_label),
        "Meter serial": tbl["serial"],
        "Last reading": tbl["reading_ts"].dt.strftime("%Y-%m-%d %H:%M").fillna("—"),
        "Reading": tbl.apply(
            lambda r: f"{r['value_display']:,.3f} {r['unit']}"
            if pd.notna(r["value_display"]) and r["utility"] == "gas"
            else (f"{r['value_display']:,.1f} {r['unit']}" if pd.notna(r["value_display"]) else "—"),
            axis=1,
        ),
        "Low battery": tbl["low_battery"].map({True: "⚠️ Yes", False: ""}),
    }
)


def _style_status(s: str) -> str:
    return f"color: white; background-color: {STATUS_COLORS.get(s, GREY)}; font-weight: 600;"


st.dataframe(
    show.style.map(_style_status, subset=["Status"]),
    width='stretch',
    hide_index=True,
    height=520,
)
st.caption(
    "Gas readings arrive from the meters in litres and are shown here in m³ "
    "(litres ÷ 1000). Electricity is shown in kWh."
)

# ---------------------------------------------------------------- import log
with st.expander("Import history (hourly SFTP job)"):
    log = get_import_log()
    if log.empty:
        st.info(
            "No imports yet. Once the GitHub Action has run against the SFTP "
            "server, each processed file will be listed here."
        )
    else:
        st.dataframe(log, width='stretch', hide_index=True)
