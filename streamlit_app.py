"""Streamlit UI — OSS/BSS Log Classifier.

Entry point for multi-page navigation. Sidebar contains project
overview and category reference shared across all pages.

Patterns: one function, one responsibility. No silent fallback.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first st call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OSS/BSS Log Classifier",
    page_icon=":material/psychology:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
page = st.navigation(
    [
        st.Page(
            "app_pages/triage.py",
            title="Analyze logs",
            icon=":material/play_arrow:",
        ),
        st.Page(
            "app_pages/logs_list.py",
            title="Sample logs",
            icon=":material/library_books:",
        ),
    ],
    position="top",
)

# ---------------------------------------------------------------------------
# Sidebar (shared across all pages)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## :material/psychology: OSS/BSS Log Classifier")
    st.caption("Automated root cause analysis for telecom support teams")
    st.space("small")

    st.markdown("### :material/robot_2: How it works")
    st.markdown(
        "1. You paste a raw log entry\n"
        "2. The parser extracts the error line\n"
        "3. An LLM classifies the error pattern\n"
        "4. You get the root cause and next action"
    )
    st.space("small")

    st.markdown("### :material/category: Error categories")
    st.markdown(
        "| Category | What it catches |\n"
        "|---|---|\n"
        "| **next-tache-error** | Task sequencing violations |\n"
        "| **state-transition-block** | Orders stuck in a state |\n"
        "| **provisioning-fault** | Config or node failures |\n"
        "| **api-integration-error** | REST / SOAP API failures |\n"
        "| **unclassified** | Everything else |"
    )
    st.space("small")

    st.markdown("### :material/lightbulb: Quick start")
    st.markdown(
        "New here? Click the **Sample logs** tab to grab a "
        "pre-built log, then switch to **Analyze logs** to run it."
    )
    st.space("small")

    st.markdown("---")
    st.caption("Backend: FastAPI on port 8000")

# ---------------------------------------------------------------------------
# Run the active page
# ---------------------------------------------------------------------------
page.run()
