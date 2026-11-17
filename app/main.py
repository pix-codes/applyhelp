import sys
from pathlib import Path

# Ensure the root directory of the project is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st

from app.ui.pages.dashboard import render_dashboard
from app.ui.pages.discovery import render_discovery
from app.ui.pages.outreach_studio import render_outreach_studio
from app.ui.pages.pipeline import render_pipeline
import importlib

# Lazy import for Settings page to avoid heavy dependencies at module load time
if False:
    from app.ui.pages.settings_page import render_settings  # placeholder for static analysis

from app.ui.pages.recommendations_page import render_recommendations

st.set_page_config(
    page_title="ApplyHelp - Job Discovery & Outreach",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("💼 ApplyHelp")
st.sidebar.caption("Personal AI-Powered Job Discovery & Cold Outreach")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Candidate Profile",
        "Discovery",
        "Outreach Studio",
        "Outreach Pipeline",
        "Settings",
        "Recommendations",
    ],
)

if page == "Dashboard":
    render_dashboard()
elif page == "Candidate Profile":
    from app.ui.pages.profile import render_candidate_profile
    render_candidate_profile()
elif page == "Discovery":
    render_discovery()
elif page == "Outreach Studio":
    render_outreach_studio()
elif page == "Outreach Pipeline":
    render_pipeline()
elif page == "Settings":
    from app.ui.pages.settings_page import render_settings
    render_settings()
elif page == "Recommendations":
    render_recommendations()
