from enum import Enum


class AnalyticsErrorCode(Enum):
    ALREADY_EXISTS = "already_exists"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    REQUIRED = "required"
    UNIQUE = "unique"
    CALCULATION_ERROR = "calculation_error"
    INVALID_DATE_RANGE = "invalid_date_range"
