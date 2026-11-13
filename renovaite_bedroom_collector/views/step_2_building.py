# Section 02: Building & Project Information
"""
Section 02: Building & Project Information view.
"""

import streamlit as st
from config.constants import GERMAN_FEDERAL_STATES, BUILDING_TYPES, OWNERSHIP_ROLES
from services.validators import check_and_display_error
from state import is_form_read_only


def render_step_2():
    read_only = is_form_read_only()
    st.subheader("Section 02: Building & Project Information")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.project_name = st.text_input(
            "Project Name / Identifier *",
            value=st.session_state.project_name,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("project_name")

        st.session_state.street_address = st.text_input(
            "Street Address (Optional)",
            value=st.session_state.street_address,
            disabled=read_only,
        )

        st.session_state.city = st.text_input(
            "City *",
            value=st.session_state.city,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("city")

        st.session_state.postal_code = st.text_input(
            "Postal Code (PLZ) *",
            value=st.session_state.postal_code,
            max_chars=5,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("postal_code")

    with col2:
        state_idx = (
            GERMAN_FEDERAL_STATES.index(st.session_state.federal_state)
            if st.session_state.federal_state in GERMAN_FEDERAL_STATES
            else None
        )
        st.session_state.federal_state = st.selectbox(
            "Federal State (Bundesland) *",
            options=GERMAN_FEDERAL_STATES,
            index=state_idx,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("federal_state")

        b_idx = (
            BUILDING_TYPES.index(st.session_state.building_type)
            if st.session_state.building_type in BUILDING_TYPES
            else None
        )
        st.session_state.building_type = st.selectbox(
            "Building Typology *",
            options=BUILDING_TYPES,
            index=b_idx,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("building_type")

        o_idx = (
            OWNERSHIP_ROLES.index(st.session_state.ownership_role)
            if st.session_state.ownership_role in OWNERSHIP_ROLES
            else None
        )
        st.session_state.ownership_role = st.selectbox(
            "Ownership Status *",
            options=OWNERSHIP_ROLES,
            index=o_idx,
            disabled=read_only,
        )
        if not read_only:
            check_and_display_error("ownership_role")
