from enum import Enum

class SupplierErrorCode(Enum):
    ALREADY_EXISTS = "already_exists"
    SERVER_ERROR = "server_error"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    REQUIRED = "required"
    UNIQUE = "unique"