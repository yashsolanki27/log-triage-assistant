"""Sample logs page — displays pre-built OSS/BSS logs for quick testing.

All log data lives in data/sample_logs.py. This page just renders it.
"""

import streamlit as st

from data.sample_logs import CATEGORIES, SAMPLE_LOGS

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("### :material/library_books: Sample logs for testing")
st.caption(
    "Pick a log below, select the text in the code block, "
    "copy it (Ctrl+C), then switch to the Analyze logs tab to classify it."
)

# ---------------------------------------------------------------------------
# Group logs by category
# ---------------------------------------------------------------------------
logs_by_category: dict[str, list[dict]] = {}
for entry in SAMPLE_LOGS:
    cat = entry["category"]
    logs_by_category.setdefault(cat, []).append(entry)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
for cat_key, cat_info in CATEGORIES.items():
    cat_logs = logs_by_category.get(cat_key, [])
    if not cat_logs:
        continue

    st.markdown(f"#### {cat_info['label']}  :gray-badge[{len(cat_logs)} logs]")
    st.caption(cat_info["description"])

    for entry in cat_logs:
        with st.container(border=True):
            c1, c2 = st.columns([4, 6])
            with c1:
                st.markdown(f"**{entry['title']}**")
                st.caption(f"Tag: `{entry['tag']}`")
            with c2:
                st.code(entry["log"], language=None, wrap_lines=True)

    st.space("small")

# ---------------------------------------------------------------------------
# Footer hint
# ---------------------------------------------------------------------------
st.info(
    ":material/arrow_forward: Switch to the **Analyze logs** tab "
    "to paste and classify any of these entries.",
    icon=":material/info:",
)
