from enum import Enum

class WarhouseErrorCode(Enum):
    SERVER_ERROR = "server_error"  # Internal server error
    INVALID = "invalid"  # Invalid data provided
    NOT_FOUND = "not_found"  # Resource not found
    REQUIRED = "required"  # Required field missing
    UNIQUE = "unique"  # Unique constraint violation
    PERMISSION_DENIED = "permission_denied" 