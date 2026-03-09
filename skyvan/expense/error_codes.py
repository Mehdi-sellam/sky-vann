from enum import Enum

class ExpenseErrorCode(Enum):
    SERVER_ERROR = "server_error"                  # General internal server error
    INVALID_DATA = "invalid_data"                  # Invalid data provided
    NOT_FOUND = "resource_not_found"      # Resource not found
    FIELD_REQUIRED = "field_required"              # Required field missing
    UNIQUE_CONSTRAINT = "unique_constraint"        # Unique constraint violation
    TYPE_NOT_VALID = "type_not_valid"      # Category does not exist or is not valid
    AMOUNT_INVALID = "amount_invalid"              # Invalid amount provided for an expense
    INSUFFICIENT_FUNDS = "insufficient_funds"      # Budget does not cover expense amount
    INVALID_DISCOUNT = "invalid_discount"          # Invalid discount applied
    INCOMPLETE_EXPENSE_ENTRY = "incomplete_expense_entry" # Missing required expense information
    PERMISSION_DENIED = "permission_denied"        # Access denied for certain operations
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"  # Duplicate resource
    INVALID_DATE_RANGE = "invalid_date_range"  # Invalid start or end date
