from django.db import transaction

from product.models import Product
from van.services import get_user_van
from .error_codes import TransferErrorCode
from .utils import (
    delete_transfer_line,
    adjust_quantities_warehouse_to_van,
    adjust_quantities_van_to_van,
    adjust_quantities_van_to_warehouse,
    adjust_quantities_warehouse_to_warehouse,
)
from .models import  Transfer, TransferLine 
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from uuid import uuid4
from .enum import REVERSE_TRANSFER_TYPE, TransferStatus, TransferType


def get_transfer_list(request):

    return Transfer.objects.filter(deleted=False).order_by("-created_at")


def get_transfer_by_uuid(uuid):

    try:
        return Transfer.objects.get(uuid=uuid, deleted=False)
    except Transfer.DoesNotExist:
        raise NotFound(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"VanAssignment with UUID {uuid} not found.",
                "fi" "eld": "uuid",
            }
        )


def get_transfer_lines(request, uuid):
    transfer = get_transfer_by_uuid(uuid)
    return transfer.lines.filter(deleted=False)


def create_transfer_line(
    transfer: Transfer,
    line: dict,
):
    """
    Create a transfer line without touching inventory.
    Inventory will be updated later on transfer acceptance.
    """

    product = line["product"]
    quantity = line["quantity"]

    if not isinstance(product, Product):
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID.value,
                "message": "Invalid product instance.",
                "field": "product",
            }
        )

    if quantity <= Decimal("0.0"):
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID.value,
                "message": "Quantity must be greater than 0.",
                "field": "quantity",
            }
        )

    try:
        TransferLine.objects.create(transfer=transfer, **line)
    except Exception as e:
        raise ValidationError(
            {
                "code": TransferErrorCode.REQUIRED.value,
                "message": str(e),
                "field": "lines",
            }
        )


@transaction.atomic
def create_transfer(requester, **data):
    """
    Creates a transfer along with its transfer lines and updates inventory accordingly.
    """
    transfer_type = data["transfer_type"]
    if transfer_type not in [choice[0] for choice in TransferType.CHOICES]:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_TRANSFER_TYPE.value,
                "message": f"Unknown transfer type: {transfer_type}",
                "field": "transfer_type",
            }
        )

    lines_data = data.pop("lines", [])

    try:
        transfer = Transfer.objects.create(**data, created_by=requester)
    except Exception as e:
        raise ValidationError(
            {
                "code": TransferErrorCode.REQUIRED.value,
                "message": f"Error: {str(e)}",
                "field": str(e),
            }
        )

        # Handle inventory updates using TransferType and create transfer lines
    for line in lines_data:
        create_transfer_line(
            transfer=transfer,
            line=line,
        )

    return transfer


@transaction.atomic
def update_transfer(requester, uuid, validated_data):
    transfer = get_transfer_by_uuid(uuid)

    if transfer.status not in [TransferStatus.DRAFT, TransferStatus.PENDING]:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_ACTION,
                "message": "Only draft or pending transfers can be updated.",
                "field": "status",
            }
        )

    # Clear existing lines
    transfer.lines.update(deleted=True)
    transfer_type = validated_data.get("transfer_type", transfer.transfer_type)

    if transfer_type == TransferType.VAN_TO_WAREHOUSE:
        transfer.source_van = validated_data.get("source_van")
        transfer.destination_warehouse = validated_data.get("destination_warehouse")
        transfer.source_warehouse = None
        transfer.destination_van = None

    elif transfer_type == TransferType.WAREHOUSE_TO_VAN:
        transfer.source_warehouse = validated_data.get("source_warehouse")
        transfer.destination_van = validated_data.get("destination_van")
        transfer.source_van = None
        transfer.destination_warehouse = None

    elif transfer_type == TransferType.WAREHOUSE_TO_WAREHOUSE:
        transfer.source_warehouse = validated_data.get("source_warehouse")
        transfer.destination_warehouse = validated_data.get("destination_warehouse")
        transfer.source_van = None
        transfer.destination_van = None

    elif transfer_type == TransferType.VAN_TO_VAN:
        transfer.source_van = validated_data.get("source_van")
        transfer.destination_van = validated_data.get("destination_van")
        transfer.source_warehouse = None
        transfer.destination_warehouse = None

    else:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_TRANSFER_TYPE,
                "message": f"Invalid transfer type: {transfer_type}",
                "field": "transfer_type",
            }
        )
    transfer.transfer_type = transfer_type
    transfer.updated_by = requester
    transfer.save()

    # Recreate new lines
    for line_data in validated_data["lines"]:
        create_transfer_line(transfer=transfer, line=line_data)

    return transfer


def delete_transfer(requester, transfer: Transfer) -> Transfer:
    if transfer.status != TransferStatus.PENDING:
        raise ValidationError(
            {
                "code": TransferErrorCode.CANNOT_DELETE.value,
                "message": "Only pending transfers can be deleted.",
                "field": "status",
            }
        )

    transfer.deleted = True
    transfer.updated_by = requester
    transfer.save()
    return transfer


def reject_transfer(requester, transfer: Transfer, reason: str = None):
    if transfer.status != TransferStatus.PENDING:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_OPERATION.value,  
                "message": "Only pending transfers can be rejected.",
                "field": "status",
            }
        )

    transfer.status = TransferStatus.REJECTED
    transfer.updated_by = requester
    if reason:
        transfer.rejection_reason = reason  # Optional field if you want
    transfer.save()
    return transfer


def accept_transfer(requester, transfer: Transfer) -> Transfer:
    if transfer.status != TransferStatus.PENDING:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_OPERATION.value,
                "message": "Only pending transfers can be accepted.",
                "field": "status",
            }
        )

    with transaction.atomic():
        for line in transfer.lines.all():
            product = line.product
            quantity = line.quantity

            if transfer.transfer_type == TransferType.WAREHOUSE_TO_VAN:
                adjust_quantities_warehouse_to_van(
                    product,
                    quantity,
                    transfer.source_warehouse,
                    transfer.destination_van,
                )
            elif transfer.transfer_type == TransferType.VAN_TO_WAREHOUSE:
                adjust_quantities_van_to_warehouse(
                    product,
                    quantity,
                    transfer.source_van,
                    transfer.destination_warehouse,
                )
            elif transfer.transfer_type == TransferType.WAREHOUSE_TO_WAREHOUSE:
                adjust_quantities_warehouse_to_warehouse(
                    product,
                    quantity,
                    transfer.source_warehouse,
                    transfer.destination_warehouse,
                )
            elif transfer.transfer_type == TransferType.VAN_TO_VAN:
                adjust_quantities_van_to_van(
                    product, quantity, transfer.source_van, transfer.destination_van
                )
            else:
                raise ValidationError(
                    {
                        "code": TransferErrorCode.INVALID_TRANSFER_TYPE.value,
                        "message": f"Invalid transfer type: {transfer.transfer_type}",
                        "field": "transfer_type",
                    }
                )

        transfer.status = TransferStatus.ACCEPTED
        transfer.updated_by = requester
        transfer.save()

    return transfer


@transaction.atomic
def reverse_and_clone_transfer(requester, original_transfer: Transfer) -> Transfer:
    if original_transfer.status != TransferStatus.ACCEPTED:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_OPERATION.value,
                "message": "Only accepted transfers can be reversed.",
                "field": "status",
            }
        )

    if original_transfer.reversed_from:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_OPERATION.value,
                "message": "Cannot reverse a transfer that is already a reversal.",
                "field": "transfer",
            }
        )
    reversed_type = REVERSE_TRANSFER_TYPE.get(original_transfer.transfer_type)
    if not reversed_type:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_TRANSFER_TYPE,
                "message": f"Cannot reverse transfer type {original_transfer.transfer_type}",
                "field": "transfer_type",
            }
        )

    # Create reversal transfer
    reversal_transfer = Transfer.objects.create(
        uuid=uuid4(),
        transfer_type=reversed_type,
        source_van=original_transfer.destination_van,
        destination_van=original_transfer.source_van,
        source_warehouse=original_transfer.destination_warehouse,
        destination_warehouse=original_transfer.source_warehouse,
        status=TransferStatus.PENDING,
        updated_by=requester,
        reversed_from=original_transfer,
    )

    # Copy and reverse lines
    for line in original_transfer.lines.filter(deleted=False):
        TransferLine.objects.create(
            uuid=uuid4(),
            transfer=reversal_transfer,
            product=line.product,
            quantity=line.quantity,
        )

    # Apply inventory adjustment for reversal
    accept_transfer(reversal_transfer)

    # Clone original as a new editable pending transfer
    cloned_transfer = Transfer.objects.create(
        uuid=uuid4(),
        transfer_type=original_transfer.transfer_type,
        source_van=original_transfer.source_van,
        destination_van=original_transfer.destination_van,
        source_warehouse=original_transfer.source_warehouse,
        destination_warehouse=original_transfer.destination_warehouse,
        updated_by=requester,
        status=TransferStatus.DRAFT,
    )

    for line in original_transfer.lines.filter(deleted=False):
        TransferLine.objects.create(
            uuid=uuid4(),
            transfer=cloned_transfer,
            product=line.product,
            quantity=line.quantity,
        )

    return cloned_transfer

def mark_transfer_as_draft(requester, uuid):
    transfer = get_transfer_by_uuid(uuid)

    if transfer.status == TransferStatus.DRAFT:
        return transfer

    if transfer.status not in [TransferStatus.PENDING]:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_ACTION.value,
                "message": "Only pending transfers can be marked as draft.",
                "field": "status",
            }
        )

    transfer.status = TransferStatus.DRAFT
    transfer.updated_by = requester
    transfer.save()
    return transfer

def mark_transfer_as_pending(requester, uuid):
    transfer = get_transfer_by_uuid(uuid)

    if transfer.status == TransferStatus.PENDING:
        return transfer

    if transfer.status not in [TransferStatus.DRAFT]:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_ACTION.value,
                "message": "Only draft transfers can be marked as pending.",
                "field": "status",
            }
        )

    transfer.status = TransferStatus.PENDING
    transfer.updated_by = requester
    transfer.save()
    return transfer

def get_my_transfer(request):
    """
    Get all TransferLines related to active van assignments for a user
    where the transfer is pending and not deleted.
    """
    # Get assigned van (or vans)
    van = get_user_van(request.user)
    if not van:
        return Transfer.objects.none()

    return Transfer.objects.filter(
            deleted=False,
            status=TransferStatus.PENDING,
            destination_van__in=van 
        ) 
