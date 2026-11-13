# Compiles structured JSON & flattened CSV exports
"""
Compiles structured JSON records and flattened CSV datasets for export.
"""

from datetime import date
from typing import Any, Dict
import pandas as pd
import streamlit as st


def compile_renovation_record() -> Dict[str, Any]:
    """
    Separates user credentials from project data and compiles all master schema fields
    into the canonical RenovAIte Now-Twin/Dream-Twin record.
    """
    return {
        "export_metadata": {
            "system": "RenovAIte Germany - Data Engine",
            "schema_version": "1.0.0",
            "timestamp": str(date.today()),
            "domain": "bedroom_renovation",
        },
        "user_profile": {
            "user_full_name": st.session_state.user_full_name.strip(),
            "email": st.session_state.email.strip().lower(),
        },
        "project_record": {
            "project_metadata": {
                "project_name": st.session_state.project_name.strip(),
                "street_address": st.session_state.street_address.strip(),
                "city": st.session_state.city.strip(),
                "postal_code": str(st.session_state.postal_code).strip(),
                "federal_state": st.session_state.federal_state or "",
                "building_type": st.session_state.building_type or "",
                "ownership_role": st.session_state.ownership_role or "",
            },
            "spatial_identification": {
                "room_name": st.session_state.room_name.strip(),
                "bedroom_usage": st.session_state.bedroom_usage or "",
            },
            "now_twin_baseline": {
                "existing_floor": st.session_state.existing_floor.strip(),
                "existing_walls": st.session_state.existing_walls.strip(),
                "existing_window": st.session_state.existing_window.strip(),
                "existing_heating": st.session_state.existing_heating.strip(),
                "observed_defects": st.session_state.observed_defects.strip(),
                "voice_transcript": st.session_state.voice_transcript.strip(),
                "photo_captions": st.session_state.photo_captions.strip(),
            },
            "dream_twin_envisioned": {
                "target_style": st.session_state.target_style.strip(),
                "target_floor": st.session_state.target_floor.strip(),
                "target_walls": st.session_state.target_walls.strip(),
                "target_window": st.session_state.target_window.strip(),
                "heating_upgrade": st.session_state.heating_upgrade.strip(),
                "built_in_storage": st.session_state.built_in_storage.strip(),
            },
            "project_guardrails": {
                "must_keep_elements": [
                    item.strip() for item in st.session_state.must_keep_elements if item.strip()
                ],
                "target_timeline": st.session_state.target_timeline.strip(),
                "general_notes": st.session_state.general_notes.strip(),
            },
        },
    }


def flatten_record_for_csv(record: Dict[str, Any]) -> pd.DataFrame:
    """Flattens the structured JSON payload into a single-row DataFrame for CSV download."""
    flat_dict = {
        "user_full_name": record["user_profile"]["user_full_name"],
        "email": record["user_profile"]["email"],
        "project_name": record["project_record"]["project_metadata"]["project_name"],
        "street_address": record["project_record"]["project_metadata"]["street_address"],
        "city": record["project_record"]["project_metadata"]["city"],
        "postal_code": record["project_record"]["project_metadata"]["postal_code"],
        "federal_state": record["project_record"]["project_metadata"]["federal_state"],
        "building_type": record["project_record"]["project_metadata"]["building_type"],
        "ownership_role": record["project_record"]["project_metadata"]["ownership_role"],
        "room_name": record["project_record"]["spatial_identification"]["room_name"],
        "bedroom_usage": record["project_record"]["spatial_identification"]["bedroom_usage"],
        "existing_floor": record["project_record"]["now_twin_baseline"]["existing_floor"],
        "existing_walls": record["project_record"]["now_twin_baseline"]["existing_walls"],
        "existing_window": record["project_record"]["now_twin_baseline"]["existing_window"],
        "existing_heating": record["project_record"]["now_twin_baseline"]["existing_heating"],
        "observed_defects": record["project_record"]["now_twin_baseline"]["observed_defects"],
        "voice_transcript": record["project_record"]["now_twin_baseline"]["voice_transcript"],
        "photo_captions": record["project_record"]["now_twin_baseline"]["photo_captions"],
        "target_style": record["project_record"]["dream_twin_envisioned"]["target_style"],
        "target_floor": record["project_record"]["dream_twin_envisioned"]["target_floor"],
        "target_walls": record["project_record"]["dream_twin_envisioned"]["target_walls"],
        "target_window": record["project_record"]["dream_twin_envisioned"]["target_window"],
        "heating_upgrade": record["project_record"]["dream_twin_envisioned"]["heating_upgrade"],
        "built_in_storage": record["project_record"]["dream_twin_envisioned"]["built_in_storage"],
        "must_keep_elements": "; ".join(
            record["project_record"]["project_guardrails"]["must_keep_elements"]
        ),
        "target_timeline": record["project_record"]["project_guardrails"]["target_timeline"],
        "general_notes": record["project_record"]["project_guardrails"]["general_notes"],
    }
    return pd.DataFrame([flat_dict])