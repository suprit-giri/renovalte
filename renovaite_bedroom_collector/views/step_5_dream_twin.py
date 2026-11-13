# Section 05: Envisioned Bedroom (Dream Twin)
"""
Section 05: Envisioned Bedroom (Dream Twin Target) view.
"""

import streamlit as st
from state import is_form_read_only


def render_step_5():
    read_only = is_form_read_only()
    st.subheader("Section 05: Envisioned Bedroom (Dream Twin Concept)")
    st.markdown("Define your target renovation vision, material selections, and performance upgrades.")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.target_style = st.text_area(
            "Aesthetic & Style Direction",
            value=st.session_state.target_style,
            height=110,
            disabled=read_only,
        )
        st.session_state.target_floor = st.text_area(
            "Target Flooring Material & Laying Pattern",
            value=st.session_state.target_floor,
            height=110,
            disabled=read_only,
        )
        st.session_state.target_walls = st.text_area(
            "Target Wall Coverings & Acoustic Treatments",
            value=st.session_state.target_walls,
            height=110,
            disabled=read_only,
        )

    with col2:
        st.session_state.target_window = st.text_area(
            "Target Window Standard & Acoustic Performance",
            value=st.session_state.target_window,
            height=110,
            disabled=read_only,
        )
        st.session_state.heating_upgrade = st.text_area(
            "Heating & Climate Upgrades",
            value=st.session_state.heating_upgrade,
            height=110,
            disabled=read_only,
        )
        st.session_state.built_in_storage = st.text_area(
            "Built-in Cabinetry & Millwork Intent",
            value=st.session_state.built_in_storage,
            height=110,
            disabled=read_only,
        )
