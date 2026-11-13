# AWS S3 Storage Service
"""
Service managing cloud storage upload, synchronization, and deletion in AWS S3.
Strictly follows functional requirements:
- Root directory per user: <email>/
- Submission directory: <current_project_number>_<name_of_the_user>/ (no parentheses)
- JSON file: json_<current_file_number>.json (e.g. json_1.json)
- Images: img_<current_file_number>.<ext> stored in the same directory as JSON
- Iterative synchronization: updates JSON in place, syncs uploaded images, deletes removed images.
Maintains hybrid execution: supports boto3 when installed, with built-in AWS SigV4 REST client fallback.
"""

import datetime
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from typing import Dict, List, Optional, Set, Tuple

from services.aws_config import get_aws_config


def sanitize_folder_name(name: str) -> str:
    """Sanitizes user name or folder component for safe S3 keys and directories."""
    cleaned = re.sub(r'[/\\?%*:|"<> ]', '_', name.strip())
    # Collapse multiple consecutive underscores
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    return cleaned or "user"


def sanitize_email_dir(email: str) -> str:
    """Sanitizes and normalizes email string for root directory naming."""
    return email.strip().lower()


def get_image_extension(filename: str = "", mime_type: str = "") -> str:
    """Determines canonical lowercase image file extension (.jpg, .png, etc.)."""
    if filename and "." in filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif"]:
            return ext
    mime = (mime_type or "").lower()
    if "png" in mime:
        return ".png"
    if "webp" in mime:
        return ".webp"
    if "heic" in mime:
        return ".heic"
    return ".jpg"


def build_s3_prefix(email: str, project_number: int, user_name: str) -> str:
    """
    Constructs the canonical S3 key prefix:
    Format: <Email id>/<current_project_number>_<name_of_the_user>/
    """
    clean_email = sanitize_email_dir(email)
    clean_name = sanitize_folder_name(user_name)
    num = max(1, int(project_number or 1))
    return f"{clean_email}/{num}_{clean_name}/"


# ============================================================================
# AWS SigV4 Native REST Implementation (Zero-dependency fallback)
# ============================================================================

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    return _sign(k_service, "aws4_request")


def _execute_sigv4_request(
    method: str,
    bucket: str,
    region: str,
    access_key: str,
    secret_key: str,
    key_path: str = "",
    query_params: Optional[Dict[str, str]] = None,
    body: bytes = b"",
    content_type: str = "application/octet-stream",
) -> Tuple[int, bytes, Dict[str, str]]:
    """Executes a signed AWS Signature Version 4 HTTP request to S3."""
    host = f"{bucket}.s3.{region}.amazonaws.com"
    endpoint_path = "/" + urllib.parse.quote(key_path.lstrip("/"), safe="/-_.!~*'()")

    sorted_query = ""
    if query_params:
        items = sorted(query_params.items())
        sorted_query = urllib.parse.urlencode(items)

    now = datetime.datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"{method}\n"
        f"{endpoint_path}\n"
        f"{sorted_query}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signature_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"https://{host}{endpoint_path}"
    if sorted_query:
        url += f"?{sorted_query}"

    req = urllib.request.Request(url, data=body if method in ["PUT", "POST"] else None, method=method)
    req.add_header("x-amz-date", amz_date)
    req.add_header("x-amz-content-sha256", payload_hash)
    req.add_header("Authorization", authorization_header)
    if method in ["PUT", "POST"] and content_type:
        req.add_header("Content-Type", content_type)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read()
            headers = dict(resp.headers)
            return resp.status, resp_body, headers
    except urllib.error.HTTPError as e:
        err_bytes = e.read()
        err_headers = dict(e.headers)
        # Automatic self-healing: if S3 returns 301 PermanentRedirect with actual bucket region
        correct_region = err_headers.get("x-amz-bucket-region")
        if e.code == 301 and correct_region and correct_region != region:
            return _execute_sigv4_request(
                method=method,
                bucket=bucket,
                region=correct_region,
                access_key=access_key,
                secret_key=secret_key,
                key_path=key_path,
                query_params=query_params,
                body=body,
                content_type=content_type,
            )
        return e.code, err_bytes, err_headers


# ============================================================================
# S3 High-Level Operations (boto3 with SigV4 fallback)
# ============================================================================

def list_s3_objects_under_prefix(bucket: str, prefix: str) -> List[str]:
    """Lists all S3 object keys under a given prefix."""
    cfg = get_aws_config()
    access_key = cfg["access_key_id"]
    secret_key = cfg["secret_access_key"]
    region = cfg["region"] or "eu-central-1"

    # Attempt boto3 first
    try:
        import boto3
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        s3 = session.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys
    except Exception:
        pass

    # SigV4 fallback
    status, body, _ = _execute_sigv4_request(
        method="GET",
        bucket=bucket,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
        query_params={"list-type": "2", "prefix": prefix},
    )
    if status == 200:
        keys = []
        try:
            root = ET.fromstring(body)
            # S3 namespace
            ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
            for elem in root.findall(".//s3:Contents/s3:Key", ns):
                if elem.text:
                    keys.append(elem.text)
            if not keys:
                for elem in root.findall(".//Contents/Key"):
                    if elem.text:
                        keys.append(elem.text)
        except Exception:
            pass
        return keys
    return []


def put_s3_object(bucket: str, key: str, body_bytes: bytes, content_type: str) -> bool:
    """Uploads or overwrites an object in S3."""
    cfg = get_aws_config()
    access_key = cfg["access_key_id"]
    secret_key = cfg["secret_access_key"]
    region = cfg["region"] or "eu-central-1"

    # Try boto3
    try:
        import boto3
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        s3 = session.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body_bytes,
            ContentType=content_type,
        )
        return True
    except Exception:
        pass

    # SigV4 fallback
    status, _, _ = _execute_sigv4_request(
        method="PUT",
        bucket=bucket,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
        key_path=key,
        body=body_bytes,
        content_type=content_type,
    )
    return status in [200, 201, 204]


def delete_s3_object(bucket: str, key: str) -> bool:
    """Deletes an object from S3."""
    cfg = get_aws_config()
    access_key = cfg["access_key_id"]
    secret_key = cfg["secret_access_key"]
    region = cfg["region"] or "eu-central-1"

    try:
        import boto3
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        s3 = session.client("s3")
        s3.delete_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        pass

    status, _, _ = _execute_sigv4_request(
        method="DELETE",
        bucket=bucket,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
        key_path=key,
    )
    return status in [200, 204]


def save_bucket_name_to_config(bucket_name: str) -> bool:
    """
    Saves the user-provided S3 bucket name to .streamlit/secrets.toml and .env.
    Keeps credentials persistent and secure.
    """
    clean_b = bucket_name.strip()
    if not clean_b:
        return False

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    secrets_path = os.path.join(base_dir, ".streamlit", "secrets.toml")
    env_path = os.path.join(base_dir, ".env")

    # 1. Update .streamlit/secrets.toml
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "AWS_S3_BUCKET_NAME" in content:
                content = re.sub(r'AWS_S3_BUCKET_NAME\s*=\s*".*?"', f'AWS_S3_BUCKET_NAME = "{clean_b}"', content)
            else:
                content += f'\nAWS_S3_BUCKET_NAME = "{clean_b}"\n'
            with open(secrets_path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception:
        pass

    # 2. Update .env
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "AWS_S3_BUCKET_NAME" in content:
                content = re.sub(r'AWS_S3_BUCKET_NAME=.*', f'AWS_S3_BUCKET_NAME={clean_b}', content)
            else:
                content += f'\nAWS_S3_BUCKET_NAME={clean_b}\n'
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception:
        pass

    return True


# ============================================================================
# Main S3 Synchronization Process
# ============================================================================

def sync_project_to_s3(
    user_email: str,
    user_name: str,
    project_number: int,
    payload: Dict,
    uploaded_images: Optional[List[Dict]] = None,
    old_s3_prefix: Optional[str] = None,
    target_bucket: Optional[str] = None,
) -> Dict:
    """
    Synchronizes project JSON and uploaded images to AWS S3:
    1. Uploads or overwrites json_1.json inside: <email>/<current_project_number>_<name_of_the_user>/
    2. Uploads all images as img_1.<ext>, img_2.<ext> in the same directory.
    3. Iteratively deletes any removed images or obsolete files from S3.
    4. If old_s3_prefix was different (e.g., user changed their name), cleans up old prefix.
    5. Returns detailed synchronization result.
    """
    now_iso = datetime.datetime.now(timezone.utc).isoformat()
    cfg = get_aws_config()

    bucket = target_bucket or cfg.get("bucket_name")
    if not bucket:
        return {
            "status": "bucket_not_configured",
            "message": "AWS credentials ready, but AWS_S3_BUCKET_NAME is not set. Data staged locally.",
            "synced_at": now_iso,
            "prefix": build_s3_prefix(user_email, project_number, user_name),
        }

    target_prefix = build_s3_prefix(user_email, project_number, user_name)
    json_filename = "json_1.json"
    json_key = f"{target_prefix}{json_filename}"

    # 1. Prepare JSON payload
    json_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    json_ok = put_s3_object(bucket, json_key, json_bytes, "application/json")
    if not json_ok:
        return {
            "status": "error",
            "error": f"Failed to upload {json_key} to S3 bucket '{bucket}'. Verify IAM permissions and bucket name.",
            "bucket": bucket,
            "prefix": target_prefix,
            "synced_at": now_iso,
        }

    # 2. Synchronize images
    active_keys: Set[str] = {json_key}
    synced_images: List[Dict] = []

    if uploaded_images:
        for idx, img in enumerate(uploaded_images, start=1):
            raw_name = img.get("name", "")
            mime = img.get("type", "image/jpeg")
            ext = get_image_extension(raw_name, mime)
            img_filename = f"img_{idx}{ext}"
            img_key = f"{target_prefix}{img_filename}"
            active_keys.add(img_key)

            img_bytes = img.get("bytes")
            if img_bytes:
                put_s3_object(bucket, img_key, img_bytes, mime)
                synced_images.append({
                    "original_name": raw_name,
                    "stored_name": img_filename,
                    "s3_key": img_key,
                    "size_bytes": len(img_bytes),
                    "mime_type": mime,
                })

    # 3. Iterative cleanup: delete removed images/obsolete files under target_prefix
    existing_keys = list_s3_objects_under_prefix(bucket, target_prefix)
    deleted_keys: List[str] = []
    for k in existing_keys:
        if k not in active_keys:
            if delete_s3_object(bucket, k):
                deleted_keys.append(k)

    # 4. Prefix migration cleanup: if folder changed, clean up previous prefix
    if old_s3_prefix and old_s3_prefix != target_prefix:
        old_keys = list_s3_objects_under_prefix(bucket, old_s3_prefix)
        for ok in old_keys:
            delete_s3_object(bucket, ok)
            deleted_keys.append(ok)

    return {
        "status": "synced",
        "bucket": bucket,
        "prefix": target_prefix,
        "json_key": json_key,
        "images": synced_images,
        "images_count": len(synced_images),
        "deleted_keys": deleted_keys,
        "synced_at": now_iso,
    }

