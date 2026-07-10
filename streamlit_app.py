"""Summer Ridge Smart Metering — Streamlit entry point."""
import streamlit as st

from src.branding import inject_css

st.set_page_config(
    page_title="Summer Ridge · Smart Metering",
    page_icon="assets/summer_ridge_logo.jpg",
    layout="wide",
)

inject_css()

pages = st.navigation(
    [
        st.Page("app_pages/installation.py", title="Installation Tracker", icon="🛠️", default=True),
        st.Page("app_pages/live_readings.py", title="Live AMR Readings", icon="📡"),
        st.Page("app_pages/stand_history.py", title="Stand History", icon="🏢"),
    ]
)

with st.sidebar:
    st.image("assets/summer_ridge_logo.jpg", width='stretch')
    st.markdown("---")

pages.run()

with st.sidebar:
    st.markdown("---")
    st.image("assets/voltano_logo.png", width='stretch')
    st.caption("Metering by Voltano Metering")
