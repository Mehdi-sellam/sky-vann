from enum import Enum


class TransferErrorCode(Enum):
    SERVER_ERROR = "server_error"  # Internal server error
    NOT_FOUND = "not_found"  # Transfer not found
    INVALID_TRANSFER_TYPE = "invalid_transfer_type"  # Invalid transfer type
    INSUFFICIENT_STOCK = (
        "insufficient_stock"  # Insufficient stock available for a product
    )
    PERMISSION_DENIED = "permission_denied"  # User does not have permission to delete
    INVALID_PRODUCT = "invalid_product"  # Product is not valid for transfer
    REQUIRED = "required"
    INVALID = "invalid"
    INVALID_OPERATION = "invalid_operation"
