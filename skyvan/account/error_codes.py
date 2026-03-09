from enum import Enum


class UserErrorCode(Enum):
    SERVER_ERROR = "server_error"  # Internal server error
    INVALID = "invalid"  # Invalid data provided
    NOT_FOUND = "not_found"  # User not found
    VALIDATION_ERROR =  "validation_error"  # Validation error occurred
    REQUIRED = "required"  # Required field missing
    UNIQUE = "unique"  # Unique constraint violation (e.g., email, phone)
    INVALID_ORGANIZATION = (
        "invalid_organization"  # Organization does not exist or is not valid
    )
    PERMISSION_DENIED = (
        "permission_denied"  # User does not have permission to perform this action
    )
    USER_CREATION_FAILED = "user_creation_failed"  # Failed to create user
    USER_UPDATE_FAILED = "user_update_failed"  # Failed to update user
    USER_DELETION_FAILED = "user_deletion_failed"  # Failed to delete user
    DUPLICATE_PHONE_EMAIL = (
        "duplicate_phone_email"  # A user with the same phone/email exists
    )
    INVALID_CREDENTIALS = "invalid_credentials"  # Incorrect login credentials
    PASSWORD_TOO_WEAK = (
        "password_too_weak"  # Password does not meet security requirements
    )
    ACCOUNT_INACTIVE = "account_inactive"  # User account is inactive
    INVALID_UUID = "invalid_uuid"  # UUID is not in the correct format
    PHONE_NOT_VERIFIED = "phone_not_verified"  # Phone number verification is required
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # Unauthorized access attempt
    SESSION_EXPIRED = "session_expired"  # User session has expired
    TOKEN_INVALID = "token_invalid"  # JWT token is invalid or expired
    FORBIDDEN_ACTION = "forbidden_action"  # Action is not allowed
    INVALID_PHONE_FORMAT = (
        "invalid_phone_format"  # Phone number is in an incorrect format
    )
    PASSWORD_RESET_FAILED = "password_reset_failed"  # Failed to reset password
    PASSWORD_CHANGE_REQUIRED = "password_change_required"  # User must change password
    MULTIPLE_LOGIN_ATTEMPTS = (
        "multiple_login_attempts"  # Too many failed login attempts
    )
