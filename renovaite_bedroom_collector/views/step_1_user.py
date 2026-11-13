# Section 01: User & Account Information
"""
Section 01: User & Account Information view.
"""

import streamlit as st
from services.validators import check_and_display_error
from state import is_form_read_only


def render_step_1():
    read_only = is_form_read_only()
    user = st.session_state.get("authenticated_user")
    if user:
        if not st.session_state.user_full_name:
            st.session_state.user_full_name = user.get("full_name", "")
        if not st.session_state.email:
            st.session_state.email = user.get("email", "")

    st.subheader("Section 01: User & Account Information")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.user_full_name = st.text_input(
            "User Full Name *",
            value=st.session_state.user_full_name,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("user_full_name")
    with col2:
        st.session_state.email = st.text_input(
            "Email Address *",
            value=st.session_state.email,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("email")
