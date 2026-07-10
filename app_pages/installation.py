"""Smart Meter Installation Tracking."""
import pandas as pd
import streamlit as st

from src.branding import ELEC_COLOR, GAS_COLOR, page_header
from src.charts import donut, installation_by_floor
from src.data import get_master
from src.master import FLOOR_ORDER

page_header("Smart Meter Installation Tracker")

master = get_master()
elec = master[master["utility"] == "elec"]
gas = master[master["utility"] == "gas"]

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Electricity meters with AMR", f"{int(elec['amr_active'].sum())} / {len(elec)}")
c2.metric("Electricity outstanding", int((~elec["amr_active"]).sum()))
c3.metric("Gas meters with AMR", f"{int(gas['amr_active'].sum())} / {len(gas)}")
c4.metric("Gas outstanding", int((~gas["amr_active"]).sum()))

d1, d2 = st.columns(2)
with d1:
    st.plotly_chart(
        donut(int(elec["amr_active"].sum()), len(elec), "Electricity", ELEC_COLOR),
        width='stretch',
    )
with d2:
    st.plotly_chart(
        donut(int(gas["amr_active"].sum()), len(gas), "Gas", GAS_COLOR),
        width='stretch',
    )

# ---------------------------------------------------------------- per floor
st.subheader("Progress per floor")
f1, f2 = st.columns(2)
with f1:
    st.plotly_chart(
        installation_by_floor(master, "elec", "Electricity — AMR per floor"),
        width='stretch',
    )
with f2:
    st.plotly_chart(
        installation_by_floor(master, "gas", "Gas — AMR per floor"),
        width='stretch',
    )

# ---------------------------------------------------------------- outstanding list
st.subheader("Outstanding installations")
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
