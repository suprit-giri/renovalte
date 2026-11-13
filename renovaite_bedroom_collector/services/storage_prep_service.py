# Cloud Storage Preparation Service
"""
Service for preparing project JSON datasets and associated uploaded images for cloud storage.
Strictly follows functional conventions:
- User directory: <Email id>
- Submission directory: <current_project_number>_<name_of_the_user> (no parentheses)
- JSON file: json_<current_file_number>.json (e.g. json_1.json)
- Images: img_<current_file_number>.<ext> stored in the same directory as JSON
- Iterative synchronization: updates JSON in place, syncs uploaded images, deletes removed images.
Maintains 1:1 parity with AWS S3 cloud storage structure.
"""

import json
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional
from services.database import get_connection
from services.s3_storage_service import (
    sanitize_folder_name,
    sanitize_email_dir,
    get_image_extension,
    build_s3_prefix,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING_DIR = os.path.join(BASE_DIR, "data", "storage_staging")


def get_project_storage_dir(email: str, project_number: int, user_name: str) -> str:
    """
    Returns the standardized directory path for a project's local cloud storage bundle.
    Structure: data/storage_staging/<Email id>/<current_project_number>_<name_of_the_user>/
    """
    clean_email = sanitize_email_dir(email or "unknown_user@example.com")
    clean_name = sanitize_folder_name(user_name or "user")
    num = max(1, int(project_number or 1))
    folder_name = f"{num}_{clean_name}"
    return os.path.join(STAGING_DIR, clean_email, folder_name)


def load_staged_project_images(
    user_id: str,
    email: str = "",
    project_number: int = 1,
    user_name: str = "",
    project_id: str = "",
) -> List[Dict]:
    """
    Loads all existing staged images for a project bundle from local storage staging into memory.
    Checks the canonical folder: data/storage_staging/<email>/<project_number>_<user_name>/
    With fallback to database storage_path and legacy folders for backward compatibility.
    """
    candidate_dirs = []

    # 1. Canonical directory
    if email and user_name:
        candidate_dirs.append(get_project_storage_dir(email, project_number, user_name))

    # 2. Check storage_path in SQLite database
    conn = get_connection()
    try:
        cur = conn.cursor()
        if project_id:
            cur.execute("SELECT storage_path, user_id, project_number FROM projects WHERE id = ?;", (project_id,))
            row = cur.fetchone()
            if row and row["storage_path"] and os.path.exists(row["storage_path"]):
                candidate_dirs.append(row["storage_path"])
        # If email was not passed, resolve user email and name from DB
        if not email and user_id:
            cur.execute("SELECT email, full_name FROM users WHERE id = ?;", (user_id,))
            u_row = cur.fetchone()
            if u_row:
                email = u_row["email"]
                if not user_name:
                    user_name = u_row["full_name"]
                candidate_dirs.append(get_project_storage_dir(email, project_number, user_name))
    except Exception:
        pass
    finally:
        conn.close()

    photos = []
    seen_fnames = set()

    for bundle_dir in candidate_dirs:
        if not os.path.exists(bundle_dir):
            continue

        # Check images directly in bundle_dir (canonical convention: img_<n>.<ext>)
        all_files = sorted(os.listdir(bundle_dir))
        img_pattern = re.compile(r"^img_(\d+)\.(jpg|jpeg|png|webp|heic|bmp|gif)$", re.IGNORECASE)

        for fname in all_files:
            if img_pattern.match(fname):
                fpath = os.path.join(bundle_dir, fname)
                if os.path.isfile(fpath) and fname not in seen_fnames:
                    try:
                        with open(fpath, "rb") as f:
                            raw_bytes = f.read()
                        mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
                        photos.append(
                            {
                                "name": fname,
                                "bytes": raw_bytes,
                                "size": len(raw_bytes),
                                "type": mime,
                            }
                        )
                        seen_fnames.add(fname)
                    except Exception:
                        continue

        # If images found in canonical directory, return them
        if photos:
            return photos

        # Check legacy images/ subfolder if any existed previously
        legacy_sub = os.path.join(bundle_dir, "images")
        if os.path.exists(legacy_sub):
            for fname in sorted(os.listdir(legacy_sub)):
                fpath = os.path.join(legacy_sub, fname)
                if os.path.isfile(fpath) and fname not in seen_fnames:
                    try:
                        with open(fpath, "rb") as f:
                            raw_bytes = f.read()
                        mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
                        photos.append(
                            {
                                "name": fname,
                                "bytes": raw_bytes,
                                "size": len(raw_bytes),
                                "type": mime,
                            }
                        )
                        seen_fnames.add(fname)
                    except Exception:
                        continue

        if photos:
            return photos

    return photos


def prepare_project_storage(
    user_id: str,
    project_id: str,
    payload: Dict,
    uploaded_images: Optional[List[Dict]] = None,
    project_number: Optional[int] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
) -> Dict:
    """
    Prepares and stages a project's JSON dataset and associated images for cloud storage:
    1. Organizes into canonical directory: data/storage_staging/<Email id>/<current_project_number>_<name_of_the_user>/
    2. Overwrites single canonical JSON file: json_1.json
    3. Stores associated images as img_<current_file_number>.<ext> in the same directory.
    4. Iteratively deletes removed or obsolete image files.
    5. Updates the local staging manifest (storage_manifest.json).
    6. Updates project record's storage status in the SQLite database.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Resolve user email and full name
    user_prof = payload.get("user_profile") or payload.get("project_record", {}).get("user_profile") or {}
    email = user_email or user_prof.get("email") or ""
    name = user_name or user_prof.get("user_full_name") or ""

    # Fallback to database user record if empty
    if not email or not name:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT email, full_name FROM users WHERE id = ?;", (user_id,))
            u_row = cur.fetchone()
            if u_row:
                if not email:
                    email = u_row["email"]
                if not name:
                    name = u_row["full_name"]
        finally:
            conn.close()

    # Resolve project number
    if project_number is None or project_number <= 0:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT project_number FROM projects WHERE id = ? AND user_id = ?;", (project_id, user_id))
            p_row = cur.fetchone()
            if p_row and p_row["project_number"]:
                project_number = int(p_row["project_number"])
            else:
                from services.project_service import get_user_next_project_number
                project_number = get_user_next_project_number(user_id)
        finally:
            conn.close()

    project_meta = payload.get("project_record", {}).get("project_metadata", {})
    project_name = project_meta.get("project_name") or "Bedroom Renovation Project"
    postal_code = str(project_meta.get("postal_code") or "").strip()

    # Standardized directory
    bundle_dir = get_project_storage_dir(email, project_number, name)
    os.makedirs(bundle_dir, exist_ok=True)

    # Clean up previous directory if storage_path was changed
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT storage_path FROM projects WHERE id = ? AND user_id = ?;", (project_id, user_id))
        row = cur.fetchone()
        if row and row["storage_path"] and row["storage_path"] != bundle_dir:
            old_path = row["storage_path"]
            if os.path.exists(old_path) and os.path.isdir(old_path):
                # If old directory had a legacy images subfolder, move them
                legacy_sub = os.path.join(old_path, "images")
                if os.path.exists(legacy_sub):
                    for item in os.listdir(legacy_sub):
                        s = os.path.join(legacy_sub, item)
                        d = os.path.join(bundle_dir, item)
                        if not os.path.exists(d):
                            shutil.move(s, d)
                shutil.rmtree(old_path, ignore_errors=True)
    finally:
        conn.close()

    # 1. Canonical JSON File: json_1.json
    json_filename = "json_1.json"
    json_file_path = os.path.join(bundle_dir, json_filename)

    # Remove any old non-canonical JSON files in bundle_dir
    for item in os.listdir(bundle_dir):
        if item.endswith(".json") and item not in [json_filename, "storage_manifest.json"]:
            try:
                os.remove(os.path.join(bundle_dir, item))
            except Exception:
                pass

    # Overwrite the canonical JSON in place
    json_content = json.dumps(payload, indent=2, ensure_ascii=False)
    with open(json_file_path, "w", encoding="utf-8") as f:
        f.write(json_content)

    # 2. Associated Images Synchronization: img_<current_file_number>.<ext>
    staged_images_meta = []
    active_image_filenames = set()

    if uploaded_images is not None:
        for idx, img in enumerate(uploaded_images, start=1):
            raw_name = img.get("name") or f"image_{idx}.jpg"
            mime = img.get("type", "image/jpeg")
            ext = get_image_extension(raw_name, mime)
            stored_name = f"img_{idx}{ext}"
            target_image_path = os.path.join(bundle_dir, stored_name)
            active_image_filenames.add(stored_name)

            img_bytes = img.get("bytes")
            if img_bytes:
                with open(target_image_path, "wb") as img_file:
                    img_file.write(img_bytes)

            file_size = (
                len(img_bytes)
                if img_bytes
                else (os.path.getsize(target_image_path) if os.path.exists(target_image_path) else img.get("size", 0))
            )

            staged_images_meta.append(
                {
                    "file_number": idx,
                    "original_name": raw_name,
                    "stored_name": stored_name,
                    "relative_path": stored_name,
                    "size_bytes": file_size,
                    "mime_type": mime,
                }
            )

        # Iteratively remove any image files that were deleted by the user from bundle_dir
        img_pattern = re.compile(r"^img_(\d+)\.(jpg|jpeg|png|webp|heic|bmp|gif)$", re.IGNORECASE)
        for existing_file in os.listdir(bundle_dir):
            if img_pattern.match(existing_file) and existing_file not in active_image_filenames:
                try:
                    os.remove(os.path.join(bundle_dir, existing_file))
                except Exception:
                    pass
    else:
        # Catalog existing images matching convention
        img_pattern = re.compile(r"^img_(\d+)\.(jpg|jpeg|png|webp|heic|bmp|gif)$", re.IGNORECASE)
        for existing_file in sorted(os.listdir(bundle_dir)):
            if img_pattern.match(existing_file):
                file_path = os.path.join(bundle_dir, existing_file)
                if os.path.isfile(file_path):
                    staged_images_meta.append(
                        {
                            "stored_name": existing_file,
                            "relative_path": existing_file,
                            "size_bytes": os.path.getsize(file_path),
                            "mime_type": "image/jpeg",
                        }
                    )

    # 3. Local Manifest (storage_manifest.json)
    s3_prefix = build_s3_prefix(email, project_number, name)
    manifest_data = {
        "system": "RenovAIte Germany - Cloud Staging Engine",
        "schema_version": "2.0.0",
        "project_id": project_id,
        "user_id": user_id,
        "user_email": email,
        "user_name": name,
        "project_number": project_number,
        "project_name": project_name,
        "postal_code": postal_code,
        "prepared_at": now_iso,
        "storage_status": "prepared_for_cloud_upload",
        "target_s3_prefix": s3_prefix,
        "files": {
            "json_payload": {
                "filename": json_filename,
                "relative_path": json_filename,
                "size_bytes": os.path.getsize(json_file_path),
            },
            "images_count": len(staged_images_meta),
            "images": staged_images_meta,
        },
    }

    manifest_path = os.path.join(bundle_dir, "storage_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=2, ensure_ascii=False)

    # 4. Update Database record with storage status & path
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE projects
                SET storage_status = 'prepared',
                    storage_path = ?,
                    submitted_at = ?,
                    image_metadata_json = ?
                WHERE id = ? AND user_id = ?;
                """,
                (
                    bundle_dir,
                    now_iso,
                    json.dumps(staged_images_meta, ensure_ascii=False),
                    project_id,
                    user_id,
                ),
            )
    finally:
        conn.close()

    return {
        "status": "prepared",
        "project_id": project_id,
        "project_number": project_number,
        "bundle_dir": bundle_dir,
        "json_filename": json_filename,
        "json_path": json_file_path,
        "images_count": len(staged_images_meta),
        "target_s3_prefix": s3_prefix,
        "prepared_at": now_iso,
    }
