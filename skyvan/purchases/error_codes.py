from enum import Enum


class PurchaseOrderErrorCode(Enum):
    SERVER_ERROR = "server_error"  # Internal server error
    INVALID = "invalid"  # Invalid data provided
    NOT_FOUND = "not_found"  # Resource not found
    REQUIRED = "required"  # Required field missing
    UNIQUE = "unique"  # Unique constraint violation
    INVALID_SUPPLIER = "invalid_supplier"  # Supplier does not exist or is not valid
    INVALID_LINE_QUANTITY = (
        "invalid_line_quantity"  # Invalid quantity provided for a line item
    )
    INSUFFICIENT_STOCK = (
        "insufficient_stock"  # Insufficient stock available for one or more products
    )
    UNRECOGNIZED_PRODUCT = (
        "unrecognized_product"  # Product associated with a line item does not exist
    )
    INVALID_DISCOUNT = "invalid_discount"  # Invalid discount provided
    INCOMPLETE_ORDER = "incomplete_order"  # The order is missing required information
    PERMISSION_DENIED = "permission_denied"
    PURCHASE_ORDER_CREATION_FAILED = "purchase_order_creation_failed"
    INVALID_PRODUCT = "invalid_product"
    PURCHASE_LINE_CREATION_FAILED="purchase_line_creation_failed"
    PURCHASE_ORDER_UPDATE_FAILED="purchase_order_update_failed"