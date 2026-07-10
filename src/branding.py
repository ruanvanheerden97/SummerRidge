"""Shared branding: Summer Ridge x Voltano Metering.

Colour language used everywhere in the app:
    Electricity -> Voltano teal  (#007095)
    Gas         -> Summer Ridge yellow (#FCD00B)
    Chrome      -> Summer Ridge navy (#193646)
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"

NAVY = "#193646"
YELLOW = "#FCD00B"
TEAL = "#007095"
GREY = "#96989A"
DARK = "#373435"
BG = "#F5F6F7"

ELEC_COLOR = TEAL
GAS_COLOR = YELLOW

OK = "#2E9E5B"
WARN = "#E8930C"
BAD = "#D64545"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _detect_mobile() -> bool:
    """Best-effort mobile detection from the browser User-Agent (Android/iPhone/iPad)."""
    try:
        import re

        ua = st.context.headers.get("User-Agent", "")
        return bool(re.search(r"Mobi|Android|iPhone|iPad", ua, re.IGNORECASE))
    except Exception:
        return False


def init_mobile_state() -> None:
    """Set the mobile flag once per session from the User-Agent."""
    if "mobile_layout" not in st.session_state:
        st.session_state["mobile_layout"] = _detect_mobile()


def is_mobile() -> bool:
    return bool(st.session_state.get("mobile_layout", False))


def metric_row(items: list[tuple], desktop_cols: int | None = None) -> None:
    """Row of st.metric tiles: one row on desktop, 2-per-row on mobile.

    items: list of (label, value) tuples.
    """
    per_row = 2 if is_mobile() else (desktop_cols or len(items))
    for i in range(0, len(items), per_row):
        chunk = items[i : i + per_row]
        cols = st.columns(per_row)
        for col, (label, value) in zip(cols, chunk):
            col.metric(label, value)


def side_by_side(render_left, render_right) -> None:
    """Two blocks side by side on desktop, stacked on mobile."""
    if is_mobile():
        render_left()
        render_right()
    else:
        c1, c2 = st.columns(2)
        with c1:
            render_left()
        with c2:
            render_right()


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background: {NAVY};
        }}
        [data-testid="stSidebar"] * {{
            color: #EAF0F4;
        }}
        [data-testid="stSidebar"] a[aria-current="page"] {{
            background: rgba(252, 208, 11, 0.15);
            border-left: 3px solid {YELLOW};
        }}
        .sr-header {{
            display: flex; align-items: center; gap: 1rem;
            background: {NAVY};
            border-radius: 12px;
            padding: 0.9rem 1.4rem;
            margin-bottom: 1.2rem;
        }}
        .sr-header img.sr {{ height: 58px; border-radius: 8px; }}
        .sr-header img.vt {{ height: 44px; background: #fff; border-radius: 8px; padding: 4px 10px; }}
        .sr-header .titles {{ flex: 1; }}
        .sr-header h1 {{
            color: #fff; font-size: 1.45rem; margin: 0; line-height: 1.2;
        }}
        .sr-header p {{
            color: {YELLOW}; margin: 0; font-size: 0.85rem;
            text-transform: uppercase; letter-spacing: 0.12em;
        }}
        div[data-testid="stMetric"] {{
            background: #fff;
            border: 1px solid #E3E6E8;
            border-left: 5px solid {YELLOW};
            border-radius: 10px;
            padding: 0.8rem 1rem;
        }}
        div[data-testid="stMetric"].elec {{ border-left-color: {TEAL}; }}
        .pill {{
            display:inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.78rem; font-weight: 600; color:#fff;
        }}

        /* ── Mobile responsiveness ─────────────────────────────── */
        @media (max-width: 740px) {{
            .block-container {{ padding: 0.6rem 0.7rem 2rem 0.7rem !important; }}
            .sr-header {{
                flex-wrap: wrap; gap: 0.5rem;
                padding: 0.7rem 0.9rem; margin-bottom: 0.8rem;
            }}
            .sr-header img.sr {{ height: 40px; }}
            .sr-header img.vt {{ height: 30px; padding: 3px 6px; }}
            .sr-header h1 {{ font-size: 1.05rem; }}
            .sr-header p {{ font-size: 0.68rem; }}
            div[data-testid="stMetric"] {{ padding: 0.45rem 0.6rem; }}
            div[data-testid="stMetricValue"],
            div[data-testid="stMetricValue"] * {{ font-size: 1.1rem !important; }}
            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricLabel"] * {{ font-size: 0.68rem !important; }}
            h1 {{ font-size: 1.3rem !important; }}
            h2 {{ font-size: 1.1rem !important; }}
            h3 {{ font-size: 1.0rem !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "Summer Ridge · Smart Metering") -> None:
    sr = _b64(ASSETS / "summer_ridge_logo.jpg")
    vt = _b64(ASSETS / "voltano_logo.png")
    st.markdown(
        f"""
        <div class="sr-header">
            <img class="sr" src="data:image/jpeg;base64,{sr}" alt="Summer Ridge"/>
            <div class="titles">
                <p>{subtitle}</p>
                <h1>{title}</h1>
            </div>
            <img class="vt" src="data:image/png;base64,{vt}" alt="Voltano Metering"/>
        </div>
        """,
        unsafe_allow_html=True,
    )


def utility_color(utility: str) -> str:
    return ELEC_COLOR if utility == "elec" else GAS_COLOR


def utility_label(utility: str) -> str:
    return "Electricity" if utility == "elec" else "Gas"
