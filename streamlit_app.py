"""Streamlit UI — Log Triage Assistant.

Text input for log paste, submit button, calls POST /triage API,
and displays classification result fields.

Patterns: one function, one responsibility. No silent fallback.
"""

import requests
import streamlit as st

st.set_page_config(
    page_title="Log Triage Assistant",
    page_icon=":material/search:",
    layout="centered",
)

st.title("Log Triage Assistant")
st.caption("Paste an OSS/BSS log entry to classify error patterns and get root cause analysis.")

API_URL = "http://localhost:8000/triage"

log_text = st.text_area(
    "Log entry",
    placeholder="Paste your log text here...",
    height=200,
    label_visibility="collapsed",
)

with st.container(horizontal=True, horizontal_alignment="right"):
    analyze_button = st.button(
        "Analyze",
        type="primary",
        icon=":material/search:",
    )

if analyze_button and log_text.strip():
    with st.spinner("Classifying..."):
        try:
            response = requests.post(API_URL, json={"log_text": log_text}, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.ConnectionError:
            st.error("Cannot connect to API server. Ensure FastAPI is running on port 8000.")
        except requests.Timeout:
            st.error("API request timed out. Please try again.")
        except requests.HTTPError as exc:
            detail = exc.response.json().get("detail", "Unknown error") if exc.response else "Unknown error"
            st.error(f"API error: {detail}")
        else:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader("Root cause summary")
                    st.write(result["root_cause_summary"])
                with col2:
                    st.subheader("Confidence")
                    st.metric(label="%", value=result["confidence"])

                st.subheader("Suggested action")
                st.write(result["suggested_action"])

                st.divider()

                col_cat, col_reason = st.columns(2)
                with col_cat:
                    st.subheader("Category")
                    st.write(result["category"])
                with col_reason:
                    st.subheader("Unclassified reason")
                    st.write(result["unclassified_reason"] or "N/A")
