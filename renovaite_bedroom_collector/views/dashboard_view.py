# User Project Dashboard View
"""
User Project Dashboard displaying personal renovation projects,
empty-state messaging, direct project creation access, reopening existing projects,
and managing AWS S3 cloud synchronization status.
"""

import os
import shutil
import streamlit as st
from services.project_service import get_user_projects, delete_project
from services.s3_storage_service import (
    list_s3_objects_under_prefix,
    delete_s3_object,
)
from state import reset_wizard_state, logout, load_project_into_wizard


def render_dashboard_view():
    """Renders the personal project management dashboard for the authenticated user."""
    user = st.session_state.get("authenticated_user")
    if not user:
        st.session_state.app_view = "auth"
        st.rerun()
        return

    # Top User Header Bar
    top_col_brand, top_col_user = st.columns([0.65, 0.35])
    with top_col_brand:
        st.markdown(
            """
            <div style="margin-bottom: 5px;">
                <h2 style="font-size: 2rem; font-weight: 700; margin: 0;">
                    RenovAIte Germany
                </h2>
                <p style="color: gray; font-size: 0.95rem; margin-top: 2px;">
                    Personal Digital Twin Portfolio & Project Dashboard
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_col_user:
        u_info, u_btn = st.columns([0.7, 0.3])
        with u_info:
            st.markdown(
                f"<div style='text-align: right; padding-top: 6px;'>"
                f"<strong>👤 {user['full_name']}</strong><br>"
                f"<span style='color: gray; font-size: 0.85rem;'>{user['email']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with u_btn:
            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🚪 Log Out", key="logout_btn", use_container_width=True):
                logout()

    st.markdown("---")

    # Fetch this user's persistent projects strictly by user_id
    user_projects = get_user_projects(user["id"])

    # Action Header with "Create New Project"
    act_col_title, act_col_btn = st.columns([0.7, 0.3])
    with act_col_title:
        st.markdown(f"### 📁 Your Renovation Projects ({len(user_projects)})")
    with act_col_btn:
        if st.button("➕ Create New Project", type="primary", use_container_width=True, key="create_proj_top_btn"):
            reset_wizard_state(user)
            st.session_state.app_view = "create_project"
            st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Case A: Empty State (New user or no existing projects)
    # -------------------------------------------------------------
    if not user_projects:
        st.markdown(
            """
            <div style="
                border: 2px dashed #4b5563;
                border-radius: 12px;
                padding: 50px 20px;
                text-align: center;
                margin: 30px 0;
                background-color: rgba(255, 255, 255, 0.02);
            ">
                <div style="font-size: 3.5rem; margin-bottom: 12px;">🛏️</div>
                <h3 style="margin-bottom: 8px;">You haven't created any projects yet</h3>
                <p style="color: gray; max-width: 520px; margin: 0 auto 24px auto; font-size: 0.95rem; line-height: 1.5;">
                    Document existing conditions (Now Twin), define target materials and energetic performance (Dream Twin),
                    and stage structured project packages for cloud storage.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _, btn_col, _ = st.columns([1, 1.5, 1])
        with btn_col:
            if st.button("🚀 Start Your First Project", type="primary", use_container_width=True, key="empty_state_create_btn"):
                reset_wizard_state(user)
                st.session_state.app_view = "create_project"
                st.rerun()
        return

    # -------------------------------------------------------------
    # Case B: Projects Exist (Organized List / Cards)
    # -------------------------------------------------------------
    for idx, proj in enumerate(user_projects):
        payload = proj.get("payload", {})
        meta = payload.get("project_record", {}).get("project_metadata", {})
        spatial = payload.get("project_record", {}).get("spatial_identification", {})
        dream = payload.get("project_record", {}).get("dream_twin_envisioned", {})

        p_num = proj.get("project_number") or (idx + 1)
        p_name = proj["project_name"] or "Untitled Renovation Project"
        room = spatial.get("room_name") or proj.get("room_name") or "Primary Bedroom"
        usage = spatial.get("bedroom_usage") or "Not Specified"
        city = proj.get("city") or meta.get("city") or "Germany"
        plz = proj.get("postal_code") or meta.get("postal_code") or ""
        created_date = proj["created_at"][:10]
        s3_status = proj.get("s3_sync_status") or "pending"
        s3_prefix = proj.get("s3_key_prefix") or ""
        image_meta = proj.get("image_metadata") or []

        with st.container(border=True):
            col_main, col_actions = st.columns([0.76, 0.24])

            with col_main:
                # Title with Project Number badge
                st.markdown(
                    f"<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 4px;'>"
                    f"<span style='background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 700;'>Project #{p_num}</span>"
                    f"<h4 style='margin: 0; display: inline;'>🛏️ {p_name}</h4>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**Room:** {room} &nbsp;|&nbsp; "
                    f"**Usage:** {usage} &nbsp;|&nbsp; "
                    f"**Location:** {city} {plz}"
                )

                # Storage & S3 info badge
                if s3_status == "synced":
                    st.markdown(
                        f"<div style='margin: 4px 0 6px 0;'>"
                        f"<span style='display:inline-block; padding: 2px 8px; border-radius: 4px; background-color: rgba(34, 197, 94, 0.15); color: #22c55e; font-size: 0.82rem; font-weight: 600;'>☁️ AWS S3 Synced</span> "
                        f"<span style='color: gray; font-size: 0.82rem;'>Prefix: <code>{s3_prefix}</code> • JSON: <code>json_1.json</code> • Photos: {len(image_meta)}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    target_dir = f"{user['email']}/{p_num}_{user['full_name']}/"
                    st.markdown(
                        f"<div style='margin: 4px 0 6px 0;'>"
                        f"<span style='display:inline-block; padding: 2px 8px; border-radius: 4px; background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 0.82rem; font-weight: 600;'>💾 Local Staged</span> "
                        f"<span style='color: gray; font-size: 0.82rem;'>Folder: <code>{target_dir}</code> • JSON: <code>json_1.json</code> • Photos: {len(image_meta)}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Summary snippet of envisioned targets
                target_summary = []
                if dream.get("target_style"):
                    target_summary.append(f"Style: {dream['target_style'][:40]}...")
                if dream.get("target_floor"):
                    target_summary.append(f"Floor: {dream['target_floor'][:40]}...")

                if target_summary:
                    st.caption(" • ".join(target_summary))

                st.caption(f"📅 Created on {created_date} &nbsp;•&nbsp; Project ID: `{proj['id'][:8]}...`")

            with col_actions:
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                if st.button("📂 Open Project", key=f"open_proj_{proj['id']}", type="primary", use_container_width=True):
                    load_project_into_wizard(proj, edit_mode=False)
                    st.session_state.app_view = "create_project"
                    st.rerun()

                if st.button("🗑️ Delete", key=f"del_proj_{proj['id']}", use_container_width=True):
                    # Clean up local staged folder
                    if proj.get("storage_path") and os.path.exists(proj["storage_path"]):
                        shutil.rmtree(proj["storage_path"], ignore_errors=True)
                    # Clean up S3 prefix if synced
                    if proj.get("s3_bucket") and proj.get("s3_key_prefix"):
                        try:
                            s3_keys = list_s3_objects_under_prefix(proj["s3_bucket"], proj["s3_key_prefix"])
                            for k in s3_keys:
                                delete_s3_object(proj["s3_bucket"], k)
                        except Exception:
                            pass
                    if delete_project(proj["id"], user["id"]):
                        st.success("Project deleted successfully.")
                        st.rerun()
