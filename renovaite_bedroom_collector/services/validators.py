# German PLZ & email validation logic
"""
Input validation functions enforcing structural standards and German geographic conventions.
"""

import re
from typing import Dict, List, Optional
import streamlit as st


def validate_email_format(email: str) -> bool:
    """Verifies that an email matches standard RFC regex conventions."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_german_plz(plz: str) -> bool:
    """Verifies German PLZ consists of exactly 5 numeric digits preserving leading zeros."""
    clean_plz = str(plz).strip()
    return clean_plz.isdigit() and len(clean_plz) == 5


def get_field_error(field_key: str) -> Optional[str]:
    """
    Evaluates the current state of a field.
    Returns:
    - Empty-field error message if empty
    - Format/input-field error message after input is entered but invalid
    - None if valid
    """
    if field_key == "user_full_name":
        if not str(st.session_state.get("user_full_name", "")).strip():
            return "User Full Name is required."

    elif field_key == "email":
        val = str(st.session_state.get("email", "")).strip()
        if not val:
            return "Email address is required."
        if not validate_email_format(val):
            return "Please provide a valid email format (e.g., owner@beispiel.de)."

    elif field_key == "project_name":
        if not str(st.session_state.get("project_name", "")).strip():
            return "Project Name / Identifier is required."

    elif field_key == "city":
        if not str(st.session_state.get("city", "")).strip():
            return "City is required."

    elif field_key == "postal_code":
        val = str(st.session_state.get("postal_code", "")).strip()
        if not val:
            return "Postal Code (PLZ) is required."
        if not validate_german_plz(val):
            return "German Postal Code (PLZ) must consist of exactly 5 numeric digits."

    elif field_key == "federal_state":
        if not st.session_state.get("federal_state"):
            return "Federal State is required."

    elif field_key == "building_type":
        if not st.session_state.get("building_type"):
            return "Building Typology is required."

    elif field_key == "ownership_role":
        if not st.session_state.get("ownership_role"):
            return "Ownership Status is required."

    elif field_key == "room_name":
        if not str(st.session_state.get("room_name", "")).strip():
            return "Bedroom Name / Identifier is required."

    elif field_key == "bedroom_usage":
        if not st.session_state.get("bedroom_usage"):
            return "Intended Functional Purpose is required."

    return None


def validate_section_dict(step: int) -> Dict[str, str]:
    """Validates required input fields per section and returns a mapping of field key to error message."""
    errors = {}
    field_map = {
        1: ["user_full_name", "email"],
        2: ["project_name", "city", "postal_code", "federal_state", "building_type", "ownership_role"],
        3: ["room_name", "bedroom_usage"],
    }
    for field in field_map.get(step, []):
        err = get_field_error(field)
        if err:
            errors[field] = err
    return errors


def validate_section(step: int) -> List[str]:
    """Validates required input fields per section before proceeding."""
    return list(validate_section_dict(step).values())


def check_and_display_error(field_key: str):
    """
    Displays validation error directly under the specific field.
    First shows the empty-field error if empty, then after entering input shows
    the format error message if invalid, or clears the error once valid.
    """
    errors = st.session_state.get("validation_errors", {})
    if field_key not in errors:
        return

    current_error = get_field_error(field_key)
    if current_error is None:
        errors.pop(field_key, None)
        return

    errors[field_key] = current_error
    st.markdown(
        f"<div style='color: #ff4b4b; font-size: 0.83rem; margin-top: -12px; margin-bottom: 12px; font-weight: 500;'>"
        f"⚠️ {current_error}"
        f"</div>",
        unsafe_allow_html=True,
    )