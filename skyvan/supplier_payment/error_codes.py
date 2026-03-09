from enum import Enum

class SupplierPaymentErrorCode(Enum):
    SERVER_ERROR = "server_error"                   # General internal server error
    INVALID_DATA = "invalid_data"                   # Invalid data provided
    NOT_FOUND = "resource_not_found"                # Payment history record not found
    FIELD_REQUIRED = "field_required"               # Required field missing
    UNIQUE_CONSTRAINT = "unique_constraint"         # Unique constraint violation
    INVALID_AMOUNT = "invalid_amount"               # Invalid transaction amount
    INVALID_TYPE = "invalid_type"                   # Invalid transaction type
    INCOMPLETE_ENTRY = "incomplete_entry"           # Missing required payment information
    PERMISSION_DENIED = "permission_denied"         # Access denied for certain operations
    SUPPLIER_PAYMENT_FAILED="supplier_payment_failed"
  