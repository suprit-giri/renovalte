# AWS S3 Configuration & Credential Provider
"""
Central provider for AWS credentials and S3 configuration.
Supports Streamlit native secrets (.streamlit/secrets.toml) and environment variables (.env),
safely keeping credentials excluded from source control.
"""

import os
from typing import Dict, Optional

try:
    import streamlit as st
except ImportError:
    st = None

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_aws_config() -> Dict[str, Optional[str]]:
    """
    Retrieves AWS credentials and S3 configuration.
    Priority order:
    1. Streamlit native secrets (.streamlit/secrets.toml)
    2. Environment variables (.env or system environment)
    """
    access_key = None
    secret_key = None
    region = None
    bucket_name = None

    # 1. Check Streamlit native secrets if running inside Streamlit
    if st is not None:
        try:
            if hasattr(st, "secrets"):
                access_key = st.secrets.get("AWS_ACCESS_KEY_ID")
                secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY")
                region = st.secrets.get("AWS_DEFAULT_REGION") or st.secrets.get("AWS_REGION")
                bucket_name = st.secrets.get("AWS_S3_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
        except Exception:
            pass

    # If not found via st.secrets, try reading .streamlit/secrets.toml directly
    if not access_key and tomllib is not None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        secrets_file = os.path.join(base_dir, ".streamlit", "secrets.toml")
        if os.path.exists(secrets_file):
            try:
                with open(secrets_file, "rb") as f:
                    toml_data = tomllib.load(f)
                    access_key = toml_data.get("AWS_ACCESS_KEY_ID")
                    secret_key = toml_data.get("AWS_SECRET_ACCESS_KEY")
                    region = toml_data.get("AWS_DEFAULT_REGION") or toml_data.get("AWS_REGION")
                    bucket_name = toml_data.get("AWS_S3_BUCKET_NAME") or toml_data.get("AWS_BUCKET_NAME")
            except Exception:
                pass

    # 2. Fall back to environment variables (.env or OS)
    if not access_key:
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
    if not secret_key:
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not region:
        region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION", "eu-central-1")
    if not bucket_name:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME") or os.getenv("AWS_BUCKET_NAME")

    # Clean bucket_name if empty string
    if bucket_name:
        bucket_name = bucket_name.strip() or None

    return {
        "access_key_id": access_key,
        "secret_access_key": secret_key,
        "region": region or "eu-central-1",
        "bucket_name": bucket_name,
        "is_configured": bool(access_key and secret_key and bucket_name),
    }
