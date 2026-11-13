# Section 03: Bedroom Identification & Usage
"""
Section 03: Bedroom Identification & Usage view.
"""

import streamlit as st
from config.constants import BEDROOM_USAGES
from services.validators import check_and_display_error
from state import is_form_read_only


def render_step_3():
    read_only = is_form_read_only()
    st.subheader("Section 03: Bedroom Identification & Spatial Context")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.room_name = st.text_input(
            "Bedroom Name / Label *",
            value=st.session_state.room_name,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("room_name")
    with col2:
        u_idx = (
            BEDROOM_USAGES.index(st.session_state.bedroom_usage)
            if st.session_state.bedroom_usage in BEDROOM_USAGES
            else None
        )
        st.session_state.bedroom_usage = st.selectbox(
            "Intended Functional Purpose *",
            options=BEDROOM_USAGES,
            index=u_idx,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("bedroom_usage")
