"""Data access for the Streamlit app.

Reads:
    * the meter register from data/Summer_Ridge_Master_Sheet.xlsx (in the repo)
    * readings from Supabase (populated hourly by the GitHub Action)

Unit handling: gas readings arrive in LITRES and are converted to m3 here
(litres / 1000) before anything is displayed. Electricity stays in kWh.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from supabase import create_client

from src.master import FLOOR_ORDER, load_master  # noqa: F401 (re-exported)

FRESH_HOURS = 26      # a healthy AMR meter reports at least daily
STALE_HOURS = 72      # older than this = offline

GAS_L_PER_M3 = 1000.0


@st.cache_resource
def _client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


@st.cache_data(ttl=300, show_spinner=False)
def get_master() -> pd.DataFrame:
    return load_master()


def _fetch_all(table_or_view: str, select: str = "*", page: int = 1000, **filters) -> pd.DataFrame:
    """Page through a table/view (Supabase caps responses at 1000 rows)."""
    sb = _client()
    frames, start = [], 0
    while True:
        q = sb.table(table_or_view).select(select).range(start, start + page - 1)
        for col, val in filters.items():
            q = q.eq(col, val)
        data = q.execute().data or []
        if not data:
            break
        frames.append(pd.DataFrame(data))
        if len(data) < page:
            break
        start += page
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_latest_readings() -> pd.DataFrame:
    df = _fetch_all("latest_readings")
    if df.empty:
        return df
    df["reading_ts"] = pd.to_datetime(df["reading_ts"], utc=True, format="ISO8601")
    df["reading_value"] = pd.to_numeric(df["reading_value"])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_meter_history(serial: str) -> pd.DataFrame:
    df = _fetch_all("readings", meter_serial=str(serial))
    if df.empty:
        return df
    df["reading_ts"] = pd.to_datetime(df["reading_ts"], utc=True, format="ISO8601")
    df["reading_value"] = pd.to_numeric(df["reading_value"])
    return df.sort_values("reading_ts").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def get_import_log(limit: int = 50) -> pd.DataFrame:
    sb = _client()
    data = (
        sb.table("import_log")
        .select("*")
        .order("processed_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    return pd.DataFrame(data)


# ---------------------------------------------------------------- helpers
def display_value(row: pd.Series) -> float:
    """Raw reading -> display units (gas litres -> m3, elec unchanged)."""
    v = float(row["reading_value"])
    return v / GAS_L_PER_M3 if row.get("utility") == "gas" else v


def display_unit(utility: str) -> str:
    return "m³" if utility == "gas" else "kWh"


def health_status(reading_ts: pd.Timestamp | None, low_battery: bool = False) -> str:
    """'Reporting' | 'Late' | 'Offline' | 'No data' (+low battery handled separately)."""
    if reading_ts is None or pd.isna(reading_ts):
        return "No data"
    age = datetime.now(timezone.utc) - reading_ts.to_pydatetime()
    if age <= timedelta(hours=FRESH_HOURS):
        return "Reporting"
    if age <= timedelta(hours=STALE_HOURS):
        return "Late"
    return "Offline"


def add_display_columns(latest: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Master register LEFT JOIN latest readings, with status/units computed.

    Every AMR-active meter appears even if it has never reported (status
    'No data') — those are exactly the ones a technician needs to see.
    """
    amr = master[master["amr_active"]].copy()
    if latest.empty:
        merged = amr.assign(
            reading_ts=pd.NaT, reading_value=pd.NA, low_battery=False
        )
    else:
        merged = amr.merge(
            latest[["meter_serial", "reading_ts", "reading_value", "low_battery"]],
            left_on="serial",
            right_on="meter_serial",
            how="left",
        )
    merged["low_battery"] = merged["low_battery"].fillna(False).astype(bool)
    merged["status"] = merged.apply(
        lambda r: health_status(r["reading_ts"], r["low_battery"]), axis=1
    )
    merged["value_display"] = merged.apply(
        lambda r: display_value(r) if pd.notna(r["reading_value"]) else None, axis=1
    )
    merged["unit"] = merged["utility"].map(display_unit)
    return merged
