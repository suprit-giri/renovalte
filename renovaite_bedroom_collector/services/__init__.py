# Services package
"""
Services package initialization with resilient exports.
"""

from .database import get_connection, init_database

try:
    from .validators import validate_email_format, validate_german_plz, validate_section, validate_section_dict, check_and_display_error
except ImportError:
    pass

try:
    from .data_export import compile_renovation_record, flatten_record_for_csv
except ImportError:
    pass

try:
    from .auth_service import register_user, login_user, get_user_by_id
except ImportError:
    pass

try:
    from .project_service import create_project, get_user_projects, get_project_by_id, delete_project, update_project
except ImportError:
    pass

try:
    from .storage_prep_service import prepare_project_storage, load_staged_project_images
except ImportError:
    pass

try:
    from .aws_config import get_aws_config
except ImportError:
    pass

try:
    from .s3_storage_service import sync_project_to_s3
except ImportError:
    pass
