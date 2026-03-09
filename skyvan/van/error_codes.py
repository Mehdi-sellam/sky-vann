from enum import Enum


class VanErrorCode(Enum):
    SERVER_ERROR = "server_error"  # Generic catch-all
    INVALID = "invalid"  # Validation errors
    NOT_FOUND = "not_found"  # Van not found
    REQUIRED = "required"  # Missing fields
    UNIQUE = "unique"  # License plate etc.
    CREATION_FAILED = "van_creation_failed"  # Failed to create van
    UPDATE_FAILED = "van_update_failed"  # Failed to update van
    DELETE_FAILED = "van_delete_failed"  # Failed to delete van
    HAS_ACTIVE_ASSIGNMENT = "van_has_active_assignment"  # Van still assigned
    HAS_STOCK = "van_has_stock"  # Van still has stock
    INVALID_DATE_RANGE = "invalid_date_range"
    OVERLAPPING_ASSIGNMENT = "overlapping_assignment"
    ALREADY_CLOSED = "already_closed"
    DUPLICATE_START = "duplicate_start"
    CANNOT_DELETE_ACTIVE = "cannot_delete_active"