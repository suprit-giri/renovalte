# Section 06: Guardrails, Constraints & Review / Submission
"""
Section 06: Guardrails, Constraints & Review / Submission view.
Supports initial project submission with automatic S3 cloud upload & local staging,
as well as read-only inspection and edit/save/cancel operations.
Strictly follows functional naming conventions:
- Root directory: <Email id>/
- Project directory: <current_project_number>_<name_of_the_user>/ (no parentheses)
- JSON file: json_1.json
- Images: img_1.<ext>, img_2.<ext> in the same directory.
"""

import streamlit as st
from services.validators import validate_section_dict
from services.data_export import compile_renovation_record
from services.project_service import create_project, get_user_next_project_number
from services.storage_prep_service import prepare_project_storage
from services.s3_storage_service import sync_project_to_s3
from state import is_form_read_only, restore_project_backup, reset_wizard_state
from views.navigation import execute_save_changes


def render_step_6():
    read_only = is_form_read_only()
    is_existing = bool(st.session_state.get("active_project_id"))

    st.subheader("Section 06: User Guardrails, Constraints & Review")
    st.markdown("Set non-negotiable boundaries, review the mapped fields, and finalize data collection.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Must-Keep Elements (Repeatable)")
        st.caption("Specify structural, artistic, or historic elements that must not be demolished.")

        elements_to_delete = []
        if read_only:
            if not st.session_state.must_keep_elements:
                st.info("No must-keep elements recorded.")
            else:
                for i, elem in enumerate(st.session_state.must_keep_elements):
                    st.text_input(f"Element #{i+1}", value=elem, key=f"must_keep_{i}", disabled=True)
        else:
            for i, elem in enumerate(st.session_state.must_keep_elements):
                sub_c1, sub_c2 = st.columns([0.85, 0.15])
                val = sub_c1.text_input(f"Element #{i+1}", value=elem, key=f"must_keep_{i}")
                st.session_state.must_keep_elements[i] = val
                if sub_c2.button("🗑️", key=f"del_must_keep_{i}"):
                    elements_to_delete.append(i)

            if elements_to_delete:
                for idx in sorted(elements_to_delete, reverse=True):
                    st.session_state.must_keep_elements.pop(idx)
                st.rerun()

            if st.button("➕ Add Another Must-Keep Element"):
                st.session_state.must_keep_elements.append("")
                st.rerun()

    with col2:
        st.session_state.target_timeline = st.text_input(
            "Target Renovation Timeline / Completion Horizon",
            value=st.session_state.target_timeline,
            disabled=read_only,
        )
        st.session_state.general_notes = st.text_area(
            "General Notes & Site Access Restrictions",
            value=st.session_state.general_notes,
            height=140,
            disabled=read_only,
        )

    st.markdown("---")

    # Case 1: Fresh submission success screen
    if not is_existing and st.session_state.submission_successful and st.session_state.submitted_project_result:
        st.success("🎉 **Project submitted successfully!**")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        nav_c1, nav_c2, nav_c3 = st.columns([1, 1.2, 1])
        with nav_c2:
            if st.button("📋 View in Project Dashboard", type="primary", use_container_width=True, key="return_dash_btn"):
                st.session_state.app_view = "dashboard"
                reset_wizard_state(st.session_state.get("authenticated_user"))
                st.rerun()

            if st.button("➕ Create Another Project", use_container_width=True, key="create_another_proj_btn"):
                reset_wizard_state(st.session_state.get("authenticated_user"))
                st.rerun()
        return

    # Case 2: Existing project actions (Read-only vs Edit mode)
    if is_existing:
        c1, c2, c3 = st.columns([1, 1.8, 1])
        with c2:
            if read_only:
                st.markdown(
                    "<p style='text-align: center; color: gray; margin-bottom: 12px;'>"
                    "This project is currently displayed in read-only mode."
                    "</p>",
                    unsafe_allow_html=True,
                )
                if st.button("✏️ Edit Project", type="primary", use_container_width=True, key="step6_switch_edit_btn"):
                    st.session_state.is_edit_mode = True
                    st.rerun()
            else:
                st.markdown(
                    "<p style='text-align: center; color: gray; margin-bottom: 12px;'>"
                    "Saving changes will update the existing project record, overwrite the cloud storage JSON file in place, and sync all associated images."
                    "</p>",
                    unsafe_allow_html=True,
                )
                sub_c1, sub_c2 = st.columns(2)
                with sub_c1:
                    if st.button("💾 Save Changes", type="primary", use_container_width=True, key="step6_save_edits_btn"):
                        execute_save_changes()
                with sub_c2:
                    if st.button("❌ Cancel", use_container_width=True, key="step6_cancel_edits_btn"):
                        restore_project_backup()
                        st.rerun()
        return

    # Case 3: Brand new project submission
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            "<p style='text-align: center; color: gray; margin-bottom: 12px;'>"
            "Confirm that all details are accurate. Submitting will automatically prepare the project's structured JSON data and all associated images for cloud storage."
            "</p>",
            unsafe_allow_html=True,
        )
        submitted = st.button("Submit", type="primary", use_container_width=True, key="submit_project_btn")

    if submitted:
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
            st.session_state.submission_successful = False
            if first_error_step:
                st.session_state.current_step = first_error_step
            st.rerun()
        else:
            st.session_state.validation_errors = {}
            compiled_record = compile_renovation_record()
            user = st.session_state.get("authenticated_user")
            user_id = user["id"] if user else "guest"
            user_email = st.session_state.email.strip()
            user_name = st.session_state.user_full_name.strip()
            uploaded_images = st.session_state.get("uploaded_photos_data", [])

            # Next sequential project number for this user
            project_number = get_user_next_project_number(user_id)

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

            # 1. Local storage staging following canonical conventions
            storage_res = prepare_project_storage(
                user_id=user_id,
                project_id="",  # will be assigned on DB insert
                payload=compiled_record,
                uploaded_images=uploaded_images,
                project_number=project_number,
                user_email=user_email,
                user_name=user_name,
            )

            # 2. Cloud AWS S3 synchronization
            s3_res = sync_project_to_s3(
                user_email=user_email,
                user_name=user_name,
                project_number=project_number,
                payload=compiled_record,
                uploaded_images=uploaded_images,
            )

            s3_status = s3_res.get("status", "pending")
            s3_bucket = s3_res.get("bucket", "")
            s3_prefix = s3_res.get("prefix", "")
            s3_json_key = s3_res.get("json_key", "")
            s3_synced_at = s3_res.get("synced_at", "")

            # 3. Persist project in SQLite database
            created = create_project(
                user_id=user_id,
                payload=compiled_record,
                project_number=project_number,
                storage_status=storage_res.get("status", "prepared"),
                storage_path=storage_res.get("bundle_dir", ""),
                submitted_at=storage_res.get("prepared_at", ""),
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

            # Update project_id in storage manifest now that ID is generated
            if created and created.get("id"):
                prepare_project_storage(
                    user_id=user_id,
                    project_id=created["id"],
                    payload=compiled_record,
                    uploaded_images=uploaded_images,
                    project_number=project_number,
                    user_email=user_email,
                    user_name=user_name,
                )

            st.session_state.current_project_number = project_number
            st.session_state.current_s3_prefix = s3_prefix
            st.session_state.submission_successful = True
            st.session_state.submitted_project_result = {**storage_res, "s3": s3_res}
            st.session_state._project_persisted_to_db = True
            st.rerun()
