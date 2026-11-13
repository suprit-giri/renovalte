# SQLite Database Initialization & Connection Provider
"""
Database layer managing persistent storage for users and associated projects.
Stores data in SQLite at data/renovaite.db.
Maintains schema migrations, project numbering, and AWS S3 cloud synchronization metadata.
"""

import os
import sqlite3
from typing import Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "renovaite.db")


def get_connection() -> sqlite3.Connection:
    """Returns a thread-safe connection to the RenovAIte SQLite database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database():
    """Initializes SQLite schema for users and projects if they do not exist."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_number INTEGER,
                project_name TEXT NOT NULL,
                room_name TEXT,
                city TEXT,
                postal_code TEXT,
                payload_json TEXT NOT NULL,
                storage_status TEXT DEFAULT 'pending',
                storage_path TEXT DEFAULT '',
                submitted_at TEXT DEFAULT '',
                image_metadata_json TEXT DEFAULT '[]',
                s3_bucket TEXT DEFAULT '',
                s3_key_prefix TEXT DEFAULT '',
                s3_json_key TEXT DEFAULT '',
                s3_sync_status TEXT DEFAULT 'pending',
                s3_synced_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);"
        )

        # Dynamic schema migration for existing databases
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(projects);")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        if "storage_status" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN storage_status TEXT DEFAULT 'pending';")
        if "storage_path" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN storage_path TEXT DEFAULT '';")
        if "submitted_at" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN submitted_at TEXT DEFAULT '';")
        if "image_metadata_json" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN image_metadata_json TEXT DEFAULT '[]';")
        if "project_number" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN project_number INTEGER;")
        if "s3_bucket" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN s3_bucket TEXT DEFAULT '';")
        if "s3_key_prefix" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN s3_key_prefix TEXT DEFAULT '';")
        if "s3_json_key" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN s3_json_key TEXT DEFAULT '';")
        if "s3_sync_status" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN s3_sync_status TEXT DEFAULT 'pending';")
        if "s3_synced_at" not in existing_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN s3_synced_at TEXT DEFAULT '';")

        # Backfill project_number for any existing records where it is unset or 0
        cursor.execute("SELECT DISTINCT user_id FROM projects WHERE project_number IS NULL OR project_number = 0;")
        users_to_backfill = [row["user_id"] for row in cursor.fetchall()]

        for uid in users_to_backfill:
            cursor.execute(
                "SELECT id, project_number FROM projects WHERE user_id = ? ORDER BY created_at ASC;",
                (uid,),
            )
            rows = cursor.fetchall()
            assigned_number = 1
            for r in rows:
                p_id = r["id"]
                conn.execute(
                    "UPDATE projects SET project_number = ? WHERE id = ?;",
                    (assigned_number, p_id),
                )
                assigned_number += 1

    conn.close()


# Ensure DB schema is ready on module import
init_database()
