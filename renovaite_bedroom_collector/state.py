# Streamlit session-state initialization & persistence
"""
Streamlit session-state initialization preserving user authentication,
multi-step wizard state, edit/read-only mode controls, and navigation context.
"""

import copy
from typing import Dict, List, Optional
import streamlit as st


def init_session_state():
    """Initializes session state defaults across the entire application."""
    # Authentication & App Navigation State
    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None

    if "app_view" not in st.session_state:
        st.session_state.app_view = "auth"  # 'auth', 'dashboard', 'create_project'

    if "active_project_id" not in st.session_state:
        st.session_state.active_project_id = None

    if "current_project_number" not in st.session_state:
        st.session_state.current_project_number = None

    if "current_s3_prefix" not in st.session_state:
        st.session_state.current_s3_prefix = ""

    if "current_s3_bucket" not in st.session_state:
        st.session_state.current_s3_bucket = ""

    if "is_edit_mode" not in st.session_state:
        st.session_state.is_edit_mode = True  # True for new projects, toggled for existing

    if "backup_project_data" not in st.session_state:
        st.session_state.backup_project_data = None

    if "backup_uploaded_photos" not in st.session_state:
        st.session_state.backup_uploaded_photos = []

    if "save_success_message" not in st.session_state:
        st.session_state.save_success_message = ""

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    if "current_step" not in st.session_state:
        st.session_state.current_step = 1

    # Section 01: User & Account Information
    if "user_full_name" not in st.session_state:
        st.session_state.user_full_name = ""
    if "email" not in st.session_state:
        st.session_state.email = ""

    # Section 02: Building & Project Information
    if "project_name" not in st.session_state:
        st.session_state.project_name = ""
    if "street_address" not in st.session_state:
        st.session_state.street_address = ""
    if "city" not in st.session_state:
        st.session_state.city = ""
    if "postal_code" not in st.session_state:
        st.session_state.postal_code = ""
    if "federal_state" not in st.session_state:
        st.session_state.federal_state = None
    if "building_type" not in st.session_state:
        st.session_state.building_type = None
    if "ownership_role" not in st.session_state:
        st.session_state.ownership_role = None

    # Section 03: Bedroom Identification & Usage
    if "room_name" not in st.session_state:
        st.session_state.room_name = ""
    if "bedroom_usage" not in st.session_state:
        st.session_state.bedroom_usage = None

    # Section 04: Existing Bedroom (Now Twin)
    if "existing_floor" not in st.session_state:
        st.session_state.existing_floor = ""
    if "existing_walls" not in st.session_state:
        st.session_state.existing_walls = ""
    if "existing_window" not in st.session_state:
        st.session_state.existing_window = ""
    if "existing_heating" not in st.session_state:
        st.session_state.existing_heating = ""
    if "observed_defects" not in st.session_state:
        st.session_state.observed_defects = ""
    if "voice_transcript" not in st.session_state:
        st.session_state.voice_transcript = ""
    if "photo_captions" not in st.session_state:
        st.session_state.photo_captions = ""

    # Section 05: Envisioned Bedroom (Dream Twin)
    if "target_style" not in st.session_state:
        st.session_state.target_style = ""
    if "target_floor" not in st.session_state:
        st.session_state.target_floor = ""
    if "target_walls" not in st.session_state:
        st.session_state.target_walls = ""
    if "target_window" not in st.session_state:
        st.session_state.target_window = ""
    if "heating_upgrade" not in st.session_state:
        st.session_state.heating_upgrade = ""
    if "built_in_storage" not in st.session_state:
        st.session_state.built_in_storage = ""

    # Section 06: Guardrails & Constraints
    if "must_keep_elements" not in st.session_state:
        st.session_state.must_keep_elements = []
    if "target_timeline" not in st.session_state:
        st.session_state.target_timeline = ""
    if "general_notes" not in st.session_state:
        st.session_state.general_notes = ""

    if "submission_successful" not in st.session_state:
        st.session_state.submission_successful = False
    if "validation_errors" not in st.session_state:
        st.session_state.validation_errors = {}
    if "uploaded_photos_data" not in st.session_state:
        st.session_state.uploaded_photos_data = []
    if "submitted_project_result" not in st.session_state:
        st.session_state.submitted_project_result = None
    if "_project_persisted_to_db" not in st.session_state:
        st.session_state._project_persisted_to_db = False


def is_form_read_only() -> bool:
    """Returns True if viewing an existing project in read-only mode."""
    return bool(st.session_state.get("active_project_id")) and not st.session_state.get("is_edit_mode", False)


def reset_wizard_state(user: Optional[Dict] = None):
    """
    Resets all 23 intake wizard fields to their clean blank state for a new project.
    Pre-populates Section 1 with the user's registered name and email if logged in.
    """
    st.session_state.active_project_id = None
    st.session_state.current_project_number = None
    st.session_state.current_s3_prefix = ""
    st.session_state.current_s3_bucket = ""
    st.session_state.is_edit_mode = True
    st.session_state.backup_project_data = None
    st.session_state.backup_uploaded_photos = []
    st.session_state.save_success_message = ""

    st.session_state.current_step = 1
    st.session_state._last_rendered_step = None
    st.session_state.submission_successful = False
    st.session_state.validation_errors = {}
    st.session_state.uploaded_photos_data = []
    st.session_state.submitted_project_result = None
    st.session_state._project_persisted_to_db = False

    if user:
        st.session_state.user_full_name = user.get("full_name", "")
        st.session_state.email = user.get("email", "")
    else:
        st.session_state.user_full_name = ""
        st.session_state.email = ""

    st.session_state.project_name = ""
    st.session_state.street_address = ""
    st.session_state.city = ""
    st.session_state.postal_code = ""
    st.session_state.federal_state = None
    st.session_state.building_type = None
    st.session_state.ownership_role = None

    st.session_state.room_name = ""
    st.session_state.bedroom_usage = None

    st.session_state.existing_floor = ""
    st.session_state.existing_walls = ""
    st.session_state.existing_window = ""
    st.session_state.existing_heating = ""
    st.session_state.observed_defects = ""
    st.session_state.voice_transcript = ""
    st.session_state.photo_captions = ""

    st.session_state.target_style = ""
    st.session_state.target_floor = ""
    st.session_state.target_walls = ""
    st.session_state.target_window = ""
    st.session_state.heating_upgrade = ""
    st.session_state.built_in_storage = ""

    st.session_state.must_keep_elements = []
    st.session_state.target_timeline = ""
    st.session_state.general_notes = ""


def load_project_into_wizard(proj: Dict, edit_mode: bool = False):
    """
    Populates all wizard session_state fields from an existing project record,
    loads associated staged media, and configures read-only or edit mode.
    """
    payload = proj.get("payload", {})
    record = payload.get("project_record", {})
    user_prof = payload.get("user_profile") or record.get("user_profile") or {}
    metadata = record.get("project_metadata", {})
    spatial = record.get("spatial_identification", {})
    now_twin = record.get("now_twin_baseline", {})
    dream_twin = record.get("dream_twin_envisioned", {})
    guardrails = record.get("project_guardrails", {})

    st.session_state.active_project_id = proj["id"]
    st.session_state.current_project_number = proj.get("project_number", 1)
    st.session_state.current_s3_prefix = proj.get("s3_key_prefix", "")
    st.session_state.current_s3_bucket = proj.get("s3_bucket", "")
    st.session_state.is_edit_mode = edit_mode
    st.session_state.current_step = 1
    st.session_state._last_rendered_step = None
    st.session_state.submission_successful = False
    st.session_state.validation_errors = {}
    st.session_state.save_success_message = ""
    st.session_state._project_persisted_to_db = True

    # Section 01
    st.session_state.user_full_name = user_prof.get("user_full_name") or proj.get("user_full_name", "")
    st.session_state.email = user_prof.get("email") or proj.get("email", "")

    # Section 02
    st.session_state.project_name = metadata.get("project_name") or proj.get("project_name", "")
    st.session_state.street_address = metadata.get("street_address", "")
    st.session_state.city = metadata.get("city") or proj.get("city", "")
    st.session_state.postal_code = str(metadata.get("postal_code") or proj.get("postal_code", ""))
    st.session_state.federal_state = metadata.get("federal_state")
    st.session_state.building_type = metadata.get("building_type")
    st.session_state.ownership_role = metadata.get("ownership_role")

    # Section 03
    st.session_state.room_name = spatial.get("room_name") or proj.get("room_name", "")
    st.session_state.bedroom_usage = spatial.get("bedroom_usage")

    # Section 04
    st.session_state.existing_floor = now_twin.get("existing_floor", "")
    st.session_state.existing_walls = now_twin.get("existing_walls", "")
    st.session_state.existing_window = now_twin.get("existing_window", "")
    st.session_state.existing_heating = now_twin.get("existing_heating", "")
    st.session_state.observed_defects = now_twin.get("observed_defects", "")
    st.session_state.voice_transcript = now_twin.get("voice_transcript", "")
    st.session_state.photo_captions = now_twin.get("photo_captions", "")

    # Section 05
    st.session_state.target_style = dream_twin.get("target_style", "")
    st.session_state.target_floor = dream_twin.get("target_floor", "")
    st.session_state.target_walls = dream_twin.get("target_walls", "")
    st.session_state.target_window = dream_twin.get("target_window", "")
    st.session_state.heating_upgrade = dream_twin.get("heating_upgrade", "")
    st.session_state.built_in_storage = dream_twin.get("built_in_storage", "")

    # Section 06
    st.session_state.must_keep_elements = list(guardrails.get("must_keep_elements", []))
    st.session_state.target_timeline = guardrails.get("target_timeline", "")
    st.session_state.general_notes = guardrails.get("general_notes", "")

    # Load associated staged images from local cloud staging directory
    from services.storage_prep_service import load_staged_project_images
    photos = load_staged_project_images(
        user_id=proj["user_id"],
        email=st.session_state.email,
        project_number=st.session_state.current_project_number,
        user_name=st.session_state.user_full_name,
        project_id=proj["id"],
    )
    st.session_state.uploaded_photos_data = photos

    # Store clean snapshot for Cancel operations
    st.session_state.backup_project_data = copy.deepcopy(payload)
    st.session_state.backup_uploaded_photos = list(photos)


def restore_project_backup():
    """Restores session state values from the backup snapshot on Cancel."""
    if not st.session_state.backup_project_data:
        st.session_state.is_edit_mode = False
        return

    payload = st.session_state.backup_project_data
    record = payload.get("project_record", {})
    user_prof = payload.get("user_profile") or record.get("user_profile") or {}
    metadata = record.get("project_metadata", {})
    spatial = record.get("spatial_identification", {})
    now_twin = record.get("now_twin_baseline", {})
    dream_twin = record.get("dream_twin_envisioned", {})
    guardrails = record.get("project_guardrails", {})

    st.session_state.user_full_name = user_prof.get("user_full_name", "")
    st.session_state.email = user_prof.get("email", "")

    st.session_state.project_name = metadata.get("project_name", "")
    st.session_state.street_address = metadata.get("street_address", "")
    st.session_state.city = metadata.get("city", "")
    st.session_state.postal_code = str(metadata.get("postal_code", ""))
    st.session_state.federal_state = metadata.get("federal_state")
    st.session_state.building_type = metadata.get("building_type")
    st.session_state.ownership_role = metadata.get("ownership_role")

    st.session_state.room_name = spatial.get("room_name", "")
    st.session_state.bedroom_usage = spatial.get("bedroom_usage")

    st.session_state.existing_floor = now_twin.get("existing_floor", "")
    st.session_state.existing_walls = now_twin.get("existing_walls", "")
    st.session_state.existing_window = now_twin.get("existing_window", "")
    st.session_state.existing_heating = now_twin.get("existing_heating", "")
    st.session_state.observed_defects = now_twin.get("observed_defects", "")
    st.session_state.voice_transcript = now_twin.get("voice_transcript", "")
    st.session_state.photo_captions = now_twin.get("photo_captions", "")

    st.session_state.target_style = dream_twin.get("target_style", "")
    st.session_state.target_floor = dream_twin.get("target_floor", "")
    st.session_state.target_walls = dream_twin.get("target_walls", "")
    st.session_state.target_window = dream_twin.get("target_window", "")
    st.session_state.heating_upgrade = dream_twin.get("heating_upgrade", "")
    st.session_state.built_in_storage = dream_twin.get("built_in_storage", "")

    st.session_state.must_keep_elements = list(guardrails.get("must_keep_elements", []))
    st.session_state.target_timeline = guardrails.get("target_timeline", "")
    st.session_state.general_notes = guardrails.get("general_notes", "")

    st.session_state.uploaded_photos_data = list(st.session_state.get("backup_uploaded_photos", []))
    st.session_state.validation_errors = {}
    st.session_state.is_edit_mode = False
    st.session_state.save_success_message = ""


def logout():
    """Clears user session and routes to the login view."""
    st.session_state.authenticated_user = None
    st.session_state.app_view = "auth"
    st.session_state.active_project_id = None
    reset_wizard_state()
    st.rerun()
