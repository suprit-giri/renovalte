# Pydantic validation schemas & data contracts
"""
Pydantic v2 data models for validating and structuring bedroom renovation records.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class UserProfileDTO(BaseModel):
    user_full_name: str = Field(..., min_length=2, description="Full name of owner/tenant")
    email: EmailStr = Field(..., description="Contact and identification email")


class ProjectMetadataDTO(BaseModel):
    project_name: str = Field(..., min_length=2)
    street_address: Optional[str] = ""
    city: str = Field(..., min_length=2)
    postal_code: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    federal_state: str
    building_type: str
    ownership_role: str


class SpatialIdentificationDTO(BaseModel):
    room_name: str = Field(..., min_length=2)
    bedroom_usage: str


class NowTwinBaselineDTO(BaseModel):
    existing_floor: Optional[str] = ""
    existing_walls: Optional[str] = ""
    existing_window: Optional[str] = ""
    existing_heating: Optional[str] = ""
    observed_defects: Optional[str] = ""
    voice_transcript: Optional[str] = ""
    photo_captions: Optional[str] = ""


class DreamTwinEnvisionedDTO(BaseModel):
    target_style: Optional[str] = ""
    target_floor: Optional[str] = ""
    target_walls: Optional[str] = ""
    target_window: Optional[str] = ""
    heating_upgrade: Optional[str] = ""
    built_in_storage: Optional[str] = ""


class ProjectGuardrailsDTO(BaseModel):
    must_keep_elements: List[str] = Field(default_factory=list)
    target_timeline: Optional[str] = ""
    general_notes: Optional[str] = ""


class MasterBedroomRenovationPayload(BaseModel):
    system: str = "RenovAIte Germany - Bedroom Renovation Intake"
    schema_version: str = "1.0.0"
    user_profile: UserProfileDTO
    project_metadata: ProjectMetadataDTO
    spatial_identification: SpatialIdentificationDTO
    now_twin_baseline: NowTwinBaselineDTO
    dream_twin_envisioned: DreamTwinEnvisionedDTO
    project_guardrails: ProjectGuardrailsDTO


class UserAccountDTO(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: str


class SavedProjectDTO(BaseModel):
    id: str
    user_id: str
    project_name: str
    room_name: Optional[str] = ""
    city: Optional[str] = ""
    postal_code: Optional[str] = ""
    payload: MasterBedroomRenovationPayload
    created_at: str
    updated_at: str