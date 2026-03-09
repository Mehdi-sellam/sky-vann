class TransferType:
    VAN_TO_WAREHOUSE = "van_to_warehouse"
    WAREHOUSE_TO_VAN = "warehouse_to_van"
    WAREHOUSE_TO_WAREHOUSE = "warehouse_to_warehouse"
    VAN_TO_VAN = "van_to_van"

    CHOICES = [
        (VAN_TO_WAREHOUSE, "Van to Warehouse"),
        (WAREHOUSE_TO_VAN, "Warehouse to Van"),
        (WAREHOUSE_TO_WAREHOUSE, "Warehouse to Warehouse"),
        (VAN_TO_VAN, "Van to Van"),
    ]


REVERSE_TRANSFER_TYPE = {
    TransferType.WAREHOUSE_TO_VAN: TransferType.VAN_TO_WAREHOUSE,
    TransferType.VAN_TO_WAREHOUSE: TransferType.WAREHOUSE_TO_VAN,
    TransferType.VAN_TO_VAN: TransferType.VAN_TO_VAN,
    TransferType.WAREHOUSE_TO_WAREHOUSE: TransferType.WAREHOUSE_TO_WAREHOUSE,
}


class TransferStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DRAFT = "draft"
    CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (DRAFT, "Draft"),
    ]
