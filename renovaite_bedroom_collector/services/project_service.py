# Project management service associating renovation digital twins with user accounts
"""
Service managing creation, retrieval, and deletion of bedroom renovation projects
associated strictly with the authenticated user.
Maintains sequential project numbering and AWS S3 cloud synchronization metadata.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from services.database import get_connection


def get_user_next_project_number(user_id: str) -> int:
    """
    Returns the next sequential project number for the given user (1, 2, 3...).
    Ensures submissions are ordered cleanly per user account.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(project_number), 0) + 1 AS next_num FROM projects WHERE user_id = ?;",
            (user_id,),
        )
        row = cur.fetchone()
        return int(row["next_num"]) if row and row["next_num"] else 1
    finally:
        conn.close()


def create_project(
    user_id: str,
    payload: Dict,
    project_number: Optional[int] = None,
    storage_status: str = "pending",
    storage_path: str = "",
    submitted_at: str = "",
    image_metadata: Optional[List[Dict]] = None,
    s3_bucket: str = "",
    s3_key_prefix: str = "",
    s3_json_key: str = "",
    s3_sync_status: str = "pending",
    s3_synced_at: str = "",
) -> Dict:
    """
    Persists a new renovation project payload linked to user_id.
    Assigns sequential project_number and records S3 cloud storage tracking fields.
    Returns the created project record.
    """
    project_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    if project_number is None or project_number <= 0:
        project_number = get_user_next_project_number(user_id)

    project_metadata = payload.get("project_record", {}).get("project_metadata", {})
    spatial = payload.get("project_record", {}).get("spatial_identification", {})

    project_name = project_metadata.get("project_name") or "Untitled Bedroom Modernization"
    room_name = spatial.get("room_name") or ""
    city = project_metadata.get("city") or ""
    postal_code = str(project_metadata.get("postal_code") or "")

    payload_json = json.dumps(payload, ensure_ascii=False)
    image_metadata_json = json.dumps(image_metadata or [], ensure_ascii=False)

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, user_id, project_number, project_name, room_name, city, postal_code,
                    payload_json, storage_status, storage_path, submitted_at,
                    image_metadata_json, s3_bucket, s3_key_prefix, s3_json_key,
                    s3_sync_status, s3_synced_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    user_id,
                    project_number,
                    project_name,
                    room_name,
                    city,
                    postal_code,
                    payload_json,
                    storage_status,
                    storage_path,
                    submitted_at,
                    image_metadata_json,
                    s3_bucket,
                    s3_key_prefix,
                    s3_json_key,
                    s3_sync_status,
                    s3_synced_at,
                    now_iso,
                    now_iso,
                ),
            )
        return {
            "id": project_id,
            "user_id": user_id,
            "project_number": project_number,
            "project_name": project_name,
            "room_name": room_name,
            "city": city,
            "postal_code": postal_code,
            "payload": payload,
            "storage_status": storage_status,
            "storage_path": storage_path,
            "submitted_at": submitted_at,
            "image_metadata": image_metadata or [],
            "s3_bucket": s3_bucket,
            "s3_key_prefix": s3_key_prefix,
            "s3_json_key": s3_json_key,
            "s3_sync_status": s3_sync_status,
            "s3_synced_at": s3_synced_at,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    finally:
        conn.close()


def get_user_projects(user_id: str) -> List[Dict]:
    """
    Returns all projects belonging to the specified user, ordered by project_number DESC.
    Ensures users can only access their own projects.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, project_number, project_name, room_name, city, postal_code,
                   payload_json, storage_status, storage_path, submitted_at,
                   image_metadata_json, s3_bucket, s3_key_prefix, s3_json_key,
                   s3_sync_status, s3_synced_at, created_at, updated_at
            FROM projects
            WHERE user_id = ?
            ORDER BY COALESCE(project_number, 0) DESC, created_at DESC;
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        projects = []
        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
            except Exception:
                payload = {}
            try:
                img_meta = json.loads(r["image_metadata_json"] or "[]")
            except Exception:
                img_meta = []
            projects.append(
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "project_number": r["project_number"] or 1,
                    "project_name": r["project_name"],
                    "room_name": r["room_name"],
                    "city": r["city"],
                    "postal_code": r["postal_code"],
                    "payload": payload,
                    "storage_status": r["storage_status"] or "pending",
                    "storage_path": r["storage_path"] or "",
                    "submitted_at": r["submitted_at"] or "",
                    "image_metadata": img_meta,
                    "s3_bucket": r["s3_bucket"] or "",
                    "s3_key_prefix": r["s3_key_prefix"] or "",
                    "s3_json_key": r["s3_json_key"] or "",
                    "s3_sync_status": r["s3_sync_status"] or "pending",
                    "s3_synced_at": r["s3_synced_at"] or "",
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
            )
        return projects
    finally:
        conn.close()


def get_project_by_id(project_id: str, user_id: str) -> Optional[Dict]:
    """
    Fetches a specific project by ID, strictly gated by user_id.
    Returns None if the project does not exist or does not belong to the user.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, project_number, project_name, room_name, city, postal_code,
                   payload_json, storage_status, storage_path, submitted_at,
                   image_metadata_json, s3_bucket, s3_key_prefix, s3_json_key,
                   s3_sync_status, s3_synced_at, created_at, updated_at
            FROM projects
            WHERE id = ? AND user_id = ?;
            """,
            (project_id, user_id),
        )
        r = cursor.fetchone()
        if not r:
            return None
        try:
            payload = json.loads(r["payload_json"])
        except Exception:
            payload = {}
        try:
            img_meta = json.loads(r["image_metadata_json"] or "[]")
        except Exception:
            img_meta = []
        return {
            "id": r["id"],
            "user_id": r["user_id"],
            "project_number": r["project_number"] or 1,
            "project_name": r["project_name"],
            "room_name": r["room_name"],
            "city": r["city"],
            "postal_code": r["postal_code"],
            "payload": payload,
            "storage_status": r["storage_status"] or "pending",
            "storage_path": r["storage_path"] or "",
            "submitted_at": r["submitted_at"] or "",
            "image_metadata": img_meta,
            "s3_bucket": r["s3_bucket"] or "",
            "s3_key_prefix": r["s3_key_prefix"] or "",
            "s3_json_key": r["s3_json_key"] or "",
            "s3_sync_status": r["s3_sync_status"] or "pending",
            "s3_synced_at": r["s3_synced_at"] or "",
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
    finally:
        conn.close()


def delete_project(project_id: str, user_id: str) -> bool:
    """
    Deletes a project belonging to user_id.
    Returns True if a record was deleted, False otherwise.
    """
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM projects WHERE id = ? AND user_id = ?;",
                (project_id, user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def update_project(
    project_id: str,
    user_id: str,
    payload: Dict,
    image_metadata: Optional[List[Dict]] = None,
    s3_bucket: Optional[str] = None,
    s3_key_prefix: Optional[str] = None,
    s3_json_key: Optional[str] = None,
    s3_sync_status: Optional[str] = None,
    s3_synced_at: Optional[str] = None,
) -> Optional[Dict]:
    """
    Updates an existing renovation project record for user_id.
    Reflects updated project metadata, room name, location, structured payload, and S3 status.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    project_metadata = payload.get("project_record", {}).get("project_metadata", {})
    spatial = payload.get("project_record", {}).get("spatial_identification", {})

    project_name = project_metadata.get("project_name") or "Untitled Bedroom Modernization"
    room_name = spatial.get("room_name") or ""
    city = project_metadata.get("city") or ""
    postal_code = str(project_metadata.get("postal_code") or "")

    payload_json = json.dumps(payload, ensure_ascii=False)

    conn = get_connection()
    try:
        with conn:
            # Build dynamic update statement based on provided optional fields
            updates = [
                "project_name = ?",
                "room_name = ?",
                "city = ?",
                "postal_code = ?",
                "payload_json = ?",
                "updated_at = ?",
            ]
            params = [project_name, room_name, city, postal_code, payload_json, now_iso]

            if image_metadata is not None:
                updates.append("image_metadata_json = ?")
                params.append(json.dumps(image_metadata, ensure_ascii=False))

            if s3_bucket is not None:
                updates.append("s3_bucket = ?")
                params.append(s3_bucket)

            if s3_key_prefix is not None:
                updates.append("s3_key_prefix = ?")
                params.append(s3_key_prefix)

            if s3_json_key is not None:
                updates.append("s3_json_key = ?")
                params.append(s3_json_key)

            if s3_sync_status is not None:
                updates.append("s3_sync_status = ?")
                params.append(s3_sync_status)

            if s3_synced_at is not None:
                updates.append("s3_synced_at = ?")
                params.append(s3_synced_at)

            params.extend([project_id, user_id])
            query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ? AND user_id = ?;"
            conn.execute(query, tuple(params))

        return get_project_by_id(project_id, user_id)
    finally:
        conn.close()
