# Section 04: Existing Bedroom (Now Twin)
"""
Section 04: Existing Bedroom (Now Twin Baseline) view.
Preserves existing project media and provides preview/delete controls during editing.
"""

import streamlit as st
from state import is_form_read_only

if hasattr(st, "dialog"):
    @st.dialog("Image Preview", width="large")
    def preview_image_dialog(photo):
        if isinstance(photo, dict):
            name = photo.get("name", "Image")
            size_kb = photo.get("size", 0) / 1024
            img_data = photo.get("bytes")
        else:
            name = photo.name
            size_kb = photo.size / 1024
            img_data = photo
        st.write(f"**{name}** ({size_kb:.1f} KB)")
        st.image(img_data, use_container_width=True)
elif hasattr(st, "experimental_dialog"):
    @st.experimental_dialog("Image Preview", width="large")
    def preview_image_dialog(photo):
        if isinstance(photo, dict):
            name = photo.get("name", "Image")
            size_kb = photo.get("size", 0) / 1024
            img_data = photo.get("bytes")
        else:
            name = photo.name
            size_kb = photo.size / 1024
            img_data = photo
        st.write(f"**{name}** ({size_kb:.1f} KB)")
        st.image(img_data, use_container_width=True)
else:
    preview_image_dialog = None


def render_step_4():
    read_only = is_form_read_only()
    st.subheader("Section 04: Existing Bedroom (Now Twin Baseline)")
    st.markdown("Document the current condition of the room before any physical renovations take place.")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.existing_floor = st.text_area(
            "Existing Flooring Substrate & Covering",
            value=st.session_state.existing_floor,
            height=100,
            disabled=read_only,
        )
        st.session_state.existing_walls = st.text_area(
            "Existing Wall & Ceiling Surfaces",
            value=st.session_state.existing_walls,
            height=100,
            disabled=read_only,
        )
        st.session_state.existing_window = st.text_area(
            "Existing Window & External Shading Profile",
            value=st.session_state.existing_window,
            height=100,
            disabled=read_only,
        )

    with col2:
        st.session_state.existing_heating = st.text_area(
            "Existing Heating Distribution & Radiator",
            value=st.session_state.existing_heating,
            height=100,
            disabled=read_only,
        )
        st.session_state.observed_defects = st.text_area(
            "Observed Defects, Thermal Leaks & Acoustic Issues",
            value=st.session_state.observed_defects,
            height=100,
            disabled=read_only,
        )
        st.session_state.voice_transcript = st.text_area(
            "Spoken Description / Voice Recording Transcript",
            value=st.session_state.voice_transcript,
            height=100,
            disabled=read_only,
        )

    st.markdown("#### Supporting Imagery & Multimodal Documentation")

    # In editable mode, allow uploading photos
    if not read_only:
        # Hide default Streamlit file list to prevent UI duplication
        st.markdown(
            """
            <style>
            [data-testid="stFileUploaderFileList"],
            [data-testid="stFileUploaderFile"],
            div[data-testid="stFileUploader"] ul,
            .stFileUploaderFileList {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        uploaded_photos = st.file_uploader(
            "Upload Room Photos (JPEG / PNG)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="now_twin_photos_uploader",
        )
        if uploaded_photos:
            existing_names = {p["name"] for p in st.session_state.uploaded_photos_data}
            for p in uploaded_photos:
                if p.name not in existing_names:
                    st.session_state.uploaded_photos_data.append(
                        {
                            "name": p.name,
                            "bytes": p.getvalue(),
                            "size": p.size,
                            "type": p.type or "image/jpeg",
                        }
                    )
                    existing_names.add(p.name)

    # Display staged/preserved photos
    staged_photos = st.session_state.get("uploaded_photos_data", [])
    if staged_photos:
        mode_label = "Read-Only" if read_only else "Attached"
        st.caption(f"📸 {len(staged_photos)} photo(s) on file ({mode_label}). Click to preview:")

        img_to_delete = None
        cols = st.columns(min(len(staged_photos), 3))
        for idx, photo in enumerate(staged_photos):
            with cols[idx % min(len(staged_photos), 3)]:
                if read_only or not preview_image_dialog:
                    if preview_image_dialog:
                        if st.button(f"🖼️ {photo['name']}", key=f"preview_img_{idx}", use_container_width=True):
                            preview_image_dialog(photo)
                    else:
                        with st.popover(f"🖼️ {photo['name']}", use_container_width=True):
                            st.image(photo["bytes"], caption=photo["name"], use_container_width=True)
                else:
                    # In edit mode, provide preview and delete option
                    c_btn, c_del = st.columns([0.8, 0.2])
                    with c_btn:
                        if st.button(f"🖼️ {photo['name']}", key=f"preview_img_{idx}", use_container_width=True):
                            preview_image_dialog(photo)
                    with c_del:
                        if st.button("🗑️", key=f"del_img_{idx}", help="Remove image"):
                            img_to_delete = idx

        if img_to_delete is not None:
            st.session_state.uploaded_photos_data.pop(img_to_delete)
            st.rerun()
    elif read_only:
        st.info("No supporting photos attached to this project.")

    st.session_state.photo_captions = st.text_area(
        "Photo Captions & Structural Annotations",
        value=st.session_state.photo_captions,
        height=80,
        disabled=read_only,
    )
