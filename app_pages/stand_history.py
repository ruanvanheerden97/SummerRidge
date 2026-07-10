"""Stand History — full reading history per stand, raw and charted."""
import pandas as pd
import streamlit as st

from src.branding import metric_row, page_header, utility_label
from src.charts import history_chart
from src.data import display_unit, get_latest_readings, get_master, get_meter_history

page_header("Stand History")

master = get_master()
latest = get_latest_readings()
serials_with_data = (
    set(latest["meter_serial"].astype(str)) if not latest.empty else set()
)

only_with_data = st.toggle(
    "Only show stands with imported readings",
    value=True,
    help="Switch off to browse every stand in the register, including those without AMR data yet.",
)

if only_with_data:
    stand_pool = master[master["serial"].isin(serials_with_data)]["stand"].unique()
else:
    stand_pool = master["stand"].unique()

stands = sorted(stand_pool)
if not stands:
    st.info("No readings have been imported yet — check the Live AMR Readings page.")
    st.stop()

stand = st.selectbox(
    "Select a stand / unit",
    stands,
    index=None,
    placeholder="Type to search, e.g. FL01/111",
)

if not stand:
    st.info(
        f"{len(stands)} stand(s) available. Pick one above to see its meters "
        "and full reading history."
    )
    st.stop()

meters = master[master["stand"] == stand].sort_values(["utility", "serial"])
meters_with_data = meters[meters["serial"].isin(serials_with_data)]
meters_without = meters[~meters["serial"].isin(serials_with_data)]

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

if not meters_without.empty:
    names = ", ".join(
        f"{utility_label(r['utility'])} {r['serial']}" for _, r in meters_without.iterrows()
    )
    st.caption(f"No imported readings yet for: {names}.")

for _, m in meters_with_data.iterrows():
    unit = display_unit(m["utility"])
    st.markdown(f"### {utility_label(m['utility'])} meter — {m['serial']}")

    hist = get_meter_history(m["serial"])
    if hist.empty:
        st.warning("No readings received yet.")
        continue

    div = 1000.0 if m["utility"] == "gas" else 1.0
    first, last = hist.iloc[0], hist.iloc[-1]
    total = (last["reading_value"] - first["reading_value"]) / div

    metric_row(
        [
            ("Readings on record", len(hist)),
            ("Latest index", f"{last['reading_value'] / div:,.3f} {unit}"),
            ("Latest reading at", last["reading_ts"].strftime("%Y-%m-%d %H:%M")),
            ("Consumption over history", f"{total:,.3f} {unit}"),
        ]
    )

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
