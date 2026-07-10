"""Smart Meter Installation Tracking."""
import pandas as pd
import streamlit as st

from src.branding import ELEC_COLOR, GAS_COLOR, is_mobile, metric_row, page_header, side_by_side
from src.charts import donut, installation_by_floor
from src.data import get_master
from src.master import FLOOR_ORDER

page_header("Smart Meter Installation Tracker")

master = get_master()
elec = master[master["utility"] == "elec"]
gas = master[master["utility"] == "gas"]

# ---------------------------------------------------------------- KPIs
metric_row(
    [
        ("Electricity meters with AMR", f"{int(elec['amr_active'].sum())} / {len(elec)}"),
        ("Electricity outstanding", int((~elec["amr_active"]).sum())),
        ("Gas meters with AMR", f"{int(gas['amr_active'].sum())} / {len(gas)}"),
        ("Gas outstanding", int((~gas["amr_active"]).sum())),
    ]
)

side_by_side(
    lambda: st.plotly_chart(
        donut(int(elec["amr_active"].sum()), len(elec), "Electricity", ELEC_COLOR),
        width='stretch',
    ),
    lambda: st.plotly_chart(
        donut(int(gas["amr_active"].sum()), len(gas), "Gas", GAS_COLOR),
        width='stretch',
    ),
)

# ---------------------------------------------------------------- per floor
st.subheader("Progress per floor")
side_by_side(
    lambda: st.plotly_chart(
        installation_by_floor(master, "elec", "Electricity — AMR per floor"),
        width='stretch',
    ),
    lambda: st.plotly_chart(
        installation_by_floor(master, "gas", "Gas — AMR per floor"),
        width='stretch',
    ),
)

# ---------------------------------------------------------------- outstanding list
st.subheader("Outstanding installations")
if is_mobile():
    util_choice = st.radio("Utility", ["Both", "Electricity", "Gas"], horizontal=True, key="inst_util")
    floor_choice = st.multiselect("Floor", FLOOR_ORDER, default=[], placeholder="All floors")
else:
    fc1, fc2 = st.columns([1, 1])
    util_choice = fc1.radio(
        "Utility", ["Both", "Electricity", "Gas"], horizontal=True, key="inst_util"
    )
    floor_choice = fc2.multiselect("Floor", FLOOR_ORDER, default=[], placeholder="All floors")

out = master[~master["amr_active"]].copy()
if util_choice == "Electricity":
    out = out[out["utility"] == "elec"]
elif util_choice == "Gas":
    out = out[out["utility"] == "gas"]
if floor_choice:
    out = out[out["floor"].isin(floor_choice)]

out = out.sort_values(["floor", "stand", "utility"])
st.caption(f"{len(out)} meter(s) still to be fitted with AMR.")
st.dataframe(
    out[["floor", "stand", "utility", "serial", "model", "parent_meter"]].rename(
        columns={
            "floor": "Floor",
            "stand": "Stand / Unit",
            "utility": "Utility",
            "serial": "Meter serial",
            "model": "Model",
            "parent_meter": "Parent meter",
        }
    ),
    width='stretch',
    hide_index=True,
)

st.download_button(
    "Download outstanding list (CSV)",
    out.to_csv(index=False).encode(),
    "summer_ridge_outstanding_amr.csv",
    "text/csv",
)

with st.expander("Stands with more than one meter"):
    st.caption(
        "Some meters feed two units (e.g. one meter covers FL01/111 and FL01/112). "
        "These stands carry more than one meter in the register; the paired unit "
        "has none and its usage is recorded on the shared meter."
    )
    multi = (
        master.groupby(["utility", "stand"]).size().reset_index(name="meters")
    )
    multi = multi[multi["meters"] > 1].sort_values(["utility", "stand"])
    st.dataframe(multi, width='stretch', hide_index=True)
