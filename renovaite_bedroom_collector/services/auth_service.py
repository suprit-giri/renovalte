# Authentication service for registration, login, and user profile management
"""
Authentication service handling secure password hashing, user registration,
and session authentication against persistent SQLite storage.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from services.database import get_connection
from services.validators import validate_email_format


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Generates a secure SHA-256 hash with a cryptographically secure random salt."""
    if not salt:
        salt = os.urandom(16).hex()
    salted = f"{salt}{password}".encode("utf-8")
    pwd_hash = hashlib.sha256(salted).hexdigest()
    return pwd_hash, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored salt and hash."""
    test_hash, _ = hash_password(password, salt=salt)
    return test_hash == stored_hash


def register_user(full_name: str, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Registers a new user account after validating input constraints.
    Returns (success, message, user_dict).
    """
    clean_name = full_name.strip()
    clean_email = email.strip().lower()

    if len(clean_name) < 2:
        return False, "Full Name must be at least 2 characters.", None

    if not clean_email or not validate_email_format(clean_email):
        return False, "Please provide a valid email address.", None

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?;", (clean_email,))
            if cursor.fetchone():
                return False, f"An account with email '{clean_email}' already exists. Please log in.", None

            user_id = str(uuid.uuid4())
            pwd_hash, salt = hash_password(password)
            created_at = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT INTO users (id, email, password_hash, salt, full_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (user_id, clean_email, pwd_hash, salt, clean_name, created_at),
            )

            user_data = {
                "id": user_id,
                "email": clean_email,
                "full_name": clean_name,
                "created_at": created_at,
            }
            return True, "Registration successful!", user_data
    except Exception as exc:
        return False, f"Registration error: {str(exc)}", None
    finally:
        conn.close()


def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Authenticates a user by email and password.
    Returns (success, message, user_dict).
    """
    clean_email = email.strip().lower()
    if not clean_email:
        return False, "Email address is required.", None

    if not password:
        return False, "Password is required.", None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, password_hash, salt, full_name, created_at FROM users WHERE email = ?;",
            (clean_email,),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Invalid email or password.", None

        if not verify_password(password, row["password_hash"], row["salt"]):
            return False, "Invalid email or password.", None

        user_data = {
            "id": row["id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "created_at": row["created_at"],
        }
        return True, "Login successful!", user_data
    except Exception as exc:
        return False, f"Login error: {str(exc)}", None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Retrieves public user profile details by user ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, full_name, created_at FROM users WHERE id = ?;",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()

