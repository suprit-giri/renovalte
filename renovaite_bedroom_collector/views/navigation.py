# Top wizard buttons, progress indicators, previous/next controls, and edit/read-only action bars
"""
Header navigation bar, progress track, previous/next controls,
and edit / read-only action bar for existing project management.
"""

import copy
import streamlit as st
from config.constants import SECTIONS
from services.validators import validate_section_dict
from services.data_export import compile_renovation_record
from services.project_service import update_project
from services.storage_prep_service import prepare_project_storage
from state import is_form_read_only, restore_project_backup, reset_wizard_state


def execute_save_changes() -> bool:
    """Validates fields, updates SQLite record and overwrites existing cloud JSON bundle in place."""
    all_errors = {}
    first_error_step = None
    for s in range(1, 4):
        errs = validate_section_dict(s)
        if errs:
            all_errors.update(errs)
            if first_error_step is None:
                first_error_step = s

    if all_errors:
        st.session_state.validation_errors.update(all_errors)
        if first_error_step:
            st.session_state.current_step = first_error_step
        st.rerun()
        return False

    st.session_state.validation_errors = {}
    user = st.session_state.get("authenticated_user")
    user_id = user["id"] if user else "guest"
    project_id = st.session_state.active_project_id
    project_number = st.session_state.get("current_project_number") or 1
    email = st.session_state.email.strip()
    user_name = st.session_state.user_full_name.strip()
    compiled_record = compile_renovation_record()
    uploaded_images = st.session_state.get("uploaded_photos_data", [])

    # Sync updated full name with user account
    if user and user_name and user_name != user.get("full_name"):
        user["full_name"] = user_name
        st.session_state.authenticated_user["full_name"] = user_name
        from services.database import get_connection
        conn = get_connection()
        try:
            with conn:
                conn.execute("UPDATE users SET full_name = ? WHERE id = ?;", (user_name, user["id"]))
        finally:
            conn.close()

    # 1. Overwrite canonical JSON file (json_1.json) and synchronize local images
    storage_res = prepare_project_storage(
        user_id=user_id,
        project_id=project_id,
        payload=compiled_record,
        uploaded_images=uploaded_images,
        project_number=project_number,
        user_email=email,
        user_name=user_name,
    )

    # 2. Iterative S3 Cloud Synchronization (updates json_1.json in place, syncs images, cleans removed)
    from services.s3_storage_service import sync_project_to_s3
    old_prefix = st.session_state.get("current_s3_prefix") or None
    s3_res = sync_project_to_s3(
        user_email=email,
        user_name=user_name,
        project_number=project_number,
        payload=compiled_record,
        uploaded_images=uploaded_images,
        old_s3_prefix=old_prefix,
    )

    s3_status = s3_res.get("status", "pending")
    s3_bucket = s3_res.get("bucket", "")
    s3_prefix = s3_res.get("prefix", "")
    s3_json_key = s3_res.get("json_key", "")
    s3_synced_at = s3_res.get("synced_at", "")

    # 3. Update SQLite database record with payload, image metadata, and S3 status
    update_project(
        project_id=project_id,
        user_id=user_id,
        payload=compiled_record,
        image_metadata=[
            {
                "original_name": img.get("name", ""),
                "size": img.get("size", 0),
                "mime_type": img.get("type", "image/jpeg"),
            }
            for img in uploaded_images
        ],
        s3_bucket=s3_bucket,
        s3_key_prefix=s3_prefix,
        s3_json_key=s3_json_key,
        s3_sync_status=s3_status,
        s3_synced_at=s3_synced_at,
    )

    # 4. Update session state snapshots and return form to read-only mode
    st.session_state.current_s3_prefix = s3_prefix
    st.session_state.backup_project_data = copy.deepcopy(compiled_record)
    st.session_state.backup_uploaded_photos = list(uploaded_images)
    st.session_state.submitted_project_result = {**storage_res, "s3": s3_res}
    st.session_state.is_edit_mode = False

    if s3_status == "synced":
        st.session_state.save_success_message = (
            f"✅ Changes saved & synced to AWS S3! `json_1.json` and images updated in `{s3_prefix}`."
        )
    elif s3_status == "bucket_not_configured":
        st.session_state.save_success_message = (
            f"✅ Changes saved! Local storage updated at `{email}/{project_number}_{user_name}/` (json_1.json overwritten in place). S3 bucket configuration pending."
        )
    else:
        st.session_state.save_success_message = (
            f"✅ Changes saved successfully! Local storage staged at `{email}/{project_number}_{user_name}/` (json_1.json updated in place)."
        )
    st.rerun()
    return True


def render_top_navigation():
    """Renders top navigation, edit/read-only mode controls, and section tracks."""
    p_name = st.session_state.project_name or "Untitled Bedroom Modernization"
    is_existing = bool(st.session_state.get("active_project_id"))
    read_only = is_form_read_only()

    # Flash success message if present
    if st.session_state.get("save_success_message"):
        st.success(st.session_state.save_success_message)
        st.session_state.save_success_message = ""

    # Mode Indicator & Action Bar for existing projects
    if is_existing:
        if read_only:
            bar_col_info, bar_col_actions = st.columns([0.65, 0.35])
            with bar_col_info:
                st.markdown(
                    """
                    <div style="
                        display: inline-block;
                        background-color: rgba(59, 130, 246, 0.1);
                        border: 1px solid rgba(59, 130, 246, 0.3);
                        border-left: 3px solid #3b82f6;
                        padding: 6px 12px;
                        border-radius: 5px;
                        font-size: 0.88rem;
                        font-weight: 600;
                        color: #1d4ed8;
                        margin-top: 3px;
                    ">
                        🔒 Read-Only Mode
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with bar_col_actions:
                c_edit, c_dash = st.columns([0.55, 0.45])
                with c_edit:
                    if st.button("✏️ Edit", type="primary", use_container_width=True, key="top_edit_mode_btn"):
                        st.session_state.is_edit_mode = True
                        st.rerun()
                with c_dash:
                    if st.button("📋 Dashboard", use_container_width=True, key="top_dash_return_btn"):
                        st.session_state.app_view = "dashboard"
                        st.session_state.active_project_id = None
                        st.rerun()
        else:
            bar_col_info, bar_col_actions = st.columns([0.55, 0.45])
            with bar_col_info:
                st.markdown(
                    f"""
                    <div style="
                        display: inline-block;
                        background-color: rgba(234, 179, 8, 0.1);
                        border: 1px solid rgba(234, 179, 8, 0.3);
                        border-left: 3px solid #eab308;
                        padding: 6px 12px;
                        border-radius: 5px;
                        font-size: 0.88rem;
                        font-weight: 600;
                        color: #b45309;
                        margin-top: 3px;
                    ">
                        ✏️ <strong>Editing Mode</strong> &nbsp;|&nbsp; Modifying project: <strong>{p_name}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with bar_col_actions:
                c_save, c_cancel, c_dash = st.columns([0.42, 0.28, 0.30])
                with c_save:
                    if st.button("💾 Save", type="primary", use_container_width=True, key="top_save_btn"):
                        execute_save_changes()
                with c_cancel:
                    if st.button("❌ Cancel", use_container_width=True, key="top_cancel_btn"):
                        restore_project_backup()
                        st.rerun()
                with c_dash:
                    if st.button("📋 Dashboard", use_container_width=True, key="top_edit_dash_btn"):
                        restore_project_backup()
                        st.session_state.app_view = "dashboard"
                        st.session_state.active_project_id = None
                        st.rerun()
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    else:
        # Creating a brand new project
        nav_head_col1, nav_head_col2 = st.columns([0.75, 0.25])
        with nav_head_col1:
            st.markdown("### 🧭 Renovation Wizard Navigation")
        with nav_head_col2:
            if st.session_state.get("authenticated_user"):
                if st.button("📋 Back to Dashboard", key="wizard_back_to_dash", use_container_width=True):
                    st.session_state.app_view = "dashboard"
                    st.rerun()

    # Section Buttons
    cols = st.columns(6)
    for idx, sec in enumerate(SECTIONS):
        is_active = st.session_state.current_step == sec["id"]
        btn_label = f"{sec['icon']} {sec['title']}"
        if is_active:
            btn_label = f"▶ {btn_label}"

        if cols[idx].button(
            btn_label,
            key=f"nav_btn_{sec['id']}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            # In edit mode, check errors when skipping forward
            if not read_only and sec["id"] > st.session_state.current_step:
                errors = validate_section_dict(st.session_state.current_step)
                if errors:
                    st.session_state.validation_errors.update(errors)
                    st.rerun()
            st.session_state.validation_errors = {}
            st.session_state.current_step = sec["id"]
            st.rerun()

    progress_value = st.session_state.current_step / len(SECTIONS)
    st.progress(progress_value)
    st.caption(
        f"Step {st.session_state.current_step} of {len(SECTIONS)}: "
        f"{SECTIONS[st.session_state.current_step - 1]['title']}"
    )
    st.markdown("---")


def render_bottom_navigation():
    """Renders Previous and Next sequential navigation controls."""
    read_only = is_form_read_only()
    st.markdown("---")
    col_prev, _, col_next = st.columns([0.25, 0.5, 0.25])

    if st.session_state.current_step > 1:
        if col_prev.button("⬅ Previous Section", use_container_width=True):
            st.session_state.current_step -= 1
            st.rerun()

    if st.session_state.current_step < len(SECTIONS):
        if col_next.button("Next Section ➡", use_container_width=True, type="primary"):
            if not read_only:
                errors = validate_section_dict(st.session_state.current_step)
                if errors:
                    st.session_state.validation_errors.update(errors)
                    st.rerun()
                    return
            st.session_state.validation_errors = {}
            st.session_state.current_step += 1
            st.rerun()
