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
