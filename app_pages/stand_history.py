"""Stand History — full reading history per stand, raw and charted."""
import pandas as pd
import streamlit as st

from src.branding import page_header, utility_label
from src.charts import history_chart
from src.data import display_unit, get_master, get_meter_history

page_header("Stand History")

master = get_master()

stands = sorted(master["stand"].unique())
stand = st.selectbox("Select a stand / unit", stands, index=None, placeholder="Type to search, e.g. FL01/111")

if not stand:
    st.info("Pick a stand above to see every meter linked to it and its full reading history.")
    st.stop()

meters = master[master["stand"] == stand].sort_values(["utility", "serial"])

st.subheader(f"Meters on {stand}")
if len(meters) > 1:
    st.caption(
        f"{stand} has {len(meters)} meters in the register. Where a stand carries "
        "two meters of the same utility, one of them usually feeds the "
        "neighbouring unit as well — its own consumption may read near zero."
    )
st.dataframe(
    meters[["utility", "serial", "model", "parent_meter", "amr_active"]].rename(
        columns={
            "utility": "Utility",
            "serial": "Meter serial",
            "model": "Model",
            "parent_meter": "Parent meter",
            "amr_active": "AMR installed",
        }
    ),
    width='stretch',
    hide_index=True,
)

for _, m in meters.iterrows():
    unit = display_unit(m["utility"])
    st.markdown(f"### {utility_label(m['utility'])} meter — {m['serial']}")

    if not m["amr_active"]:
        st.info("AMR not yet installed on this meter — no automatic readings available.")
        continue

    hist = get_meter_history(m["serial"])
    if hist.empty:
        st.warning("AMR installed but no readings received yet.")
        continue

    div = 1000.0 if m["utility"] == "gas" else 1.0
    first, last = hist.iloc[0], hist.iloc[-1]
    total = (last["reading_value"] - first["reading_value"]) / div

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Readings on record", len(hist))
    k2.metric("Latest index", f"{last['reading_value'] / div:,.3f} {unit}")
    k3.metric("Latest reading at", last["reading_ts"].strftime("%Y-%m-%d %H:%M"))
    k4.metric("Consumption over history", f"{total:,.3f} {unit}")

    st.plotly_chart(
        history_chart(hist, m["serial"], m["utility"], unit),
        width='stretch',
    )

    with st.expander(f"Raw readings — {m['serial']}"):
        raw = hist.copy().sort_values("reading_ts", ascending=False)
        raw["reading_display"] = raw["reading_value"] / div
        out = raw[
            ["reading_ts", "reading_value", "reading_display", "peak", "std",
             "offpeak", "md", "low_battery", "source_file"]
        ].rename(
            columns={
                "reading_ts": "Reading time",
                "reading_value": "Raw value (as received)",
                "reading_display": f"Value ({unit})",
                "peak": "Peak",
                "std": "Std",
                "offpeak": "Off-peak",
                "md": "MD",
                "low_battery": "Low battery",
                "source_file": "Source file",
            }
        )
        st.dataframe(out, width='stretch', hide_index=True)
        st.download_button(
            f"Download history for {m['serial']} (CSV)",
            out.to_csv(index=False).encode(),
            f"{stand.replace('/', '_')}_{m['serial']}_history.csv",
            "text/csv",
            key=f"dl_{m['serial']}",
        )
