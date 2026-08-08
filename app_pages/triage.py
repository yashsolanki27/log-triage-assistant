"""Analyze logs page — paste a log, classify it, see results."""

import requests
import streamlit as st

API_URL = "http://localhost:8000/triage"

st.markdown("### :material/edit_note: Paste your log entry")
st.caption(
    "Drop in any raw OSS/BSS log line. The classifier will identify "
    "the error pattern, root cause, and suggest a next action."
)

with st.container(border=True):
    log_text = st.text_area(
        "Log entry",
        placeholder=(
            "Example:\n"
            "2026-08-04 10:23:11 ERROR [OrderProcessor] Failed to transition "
            "order #4821 from PROVISIONING to ACTIVE: state machine blocked "
            "on dependency check"
        ),
        height=200,
        label_visibility="collapsed",
    )

    col_spacer, col_btn = st.columns([6, 1])
    with col_btn:
        analyze_clicked = st.button(
            "Classify log",
            type="primary",
            icon=":material/search:",
            use_container_width=True,
        )

# --- Results ---
if analyze_clicked and log_text.strip():
    with st.spinner("Analyzing error pattern..."):
        try:
            response = requests.post(
                API_URL, json={"log_text": log_text}, timeout=30
            )
            response.raise_for_status()
            result = response.json()
        except requests.ConnectionError:
            st.error(
                "Cannot reach the API server. "
                "Make sure FastAPI is running on port 8000.",
                icon=":material/wifi_off:",
            )
            st.stop()
        except requests.Timeout:
            st.error(
                "Request timed out. Try a shorter log or try again.",
                icon=":material/schedule:",
            )
            st.stop()
        except requests.HTTPError as exc:
            detail = (
                exc.response.json().get("detail", "Unknown error")
                if exc.response
                else "Unknown error"
            )
            st.error(f"API error: {detail}", icon=":material/error:")
            st.stop()

    st.success("Classification complete", icon=":material/check_circle:")

    # -- Key metrics --
    m1, m2, m3 = st.columns(3)
    with m1:
        category = result["category"]
        cat_colors = {
            "next-tache-error": "blue",
            "state-transition-block": "orange",
            "provisioning-fault": "red",
            "api-integration-error": "violet",
            "unclassified": "gray",
        }
        st.markdown("##### Detected category")
        st.badge(category, color=cat_colors.get(category, "gray"))
    with m2:
        confidence = result["confidence"]
        conf_color = (
            "green"
            if confidence >= 80
            else ("orange" if confidence >= 60 else "red")
        )
        st.markdown("##### Confidence score")
        st.badge(f"{confidence}%", color=conf_color)
    with m3:
        st.markdown("##### Verdict")
        if category == "unclassified":
            st.badge("Needs manual review", color="orange")
        else:
            st.badge("Classified", color="green")

    st.space("small")

    # -- Root cause --
    with st.container(border=True):
        st.markdown("##### :material/psychology: Root cause")
        st.markdown(result["root_cause_summary"])

    # -- Suggested action --
    with st.container(border=True):
        st.markdown("##### :material/next_plan: Suggested next action")
        st.markdown(result["suggested_action"])

    # -- Unclassified reason (if present) --
    if result.get("unclassified_reason"):
        st.space("small")
        with st.container(border=True):
            st.markdown("##### :material/help: Why it is unclassified")
            st.markdown(result["unclassified_reason"])

elif analyze_clicked and not log_text.strip():
    st.warning(
        "Paste a log entry first, then hit Classify.",
        icon=":material/warning:",
    )
