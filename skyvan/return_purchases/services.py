from django.db import transaction
from .models import *
from warehouse.inventory import *
from supplier_payment.services import *
from supplier_payment.enum import *
from rest_framework.exceptions import ValidationError
from .error_codes import *
from supplier_payment.models import *
from decimal import Decimal


def get_return_purchase_line_report(request):
    return ReturnPurchaseLine.objects.filter(
        return_purchase_order__deleted=False, deleted=False
    ).order_by("-created_at")

def get_return_purchases_list () :
    return ReturnPurchaseOrder.objects.filter(deleted=False)

@transaction.atomic
def create_return_purchase_order(requester, validated_data):
    try:
        # Extract nested data
        lines_data = validated_data.pop("lines", [])
        supplier_payment_data = validated_data.pop("supplier_payment", None)
        warehouse = validated_data.pop("warehouse", None)

        # Validate warehouse
        if not warehouse:
            raise ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )

        # Create the ReturnPurchaseOrder

        try:
            validated_data["date"] = validated_data.get("date", None)
            return_purchase_order = ReturnPurchaseOrder.objects.create(
                **validated_data, warehouse=warehouse, created_by=requester
            )
        except Exception as order_exception:
            raise ValidationError(
                {
                    "code": "RETURN_PURCHASE_ORDER_CREATION_FAILED",
                    "message": f"Failed to create return purchase order: {str(order_exception)}",
                    "field": "return_purchase_order",
                }
            ) from order_exception

        # Create ReturnPurchaseLine entries

        try:
            for line_data in lines_data:
                ReturnPurchaseLine.objects.create(
                    return_purchase_order=return_purchase_order, **line_data
                )
        except Exception as line_exception:
            raise ValidationError(
                {
                    "code": "RETURN_PURCHASE_LINE_CREATION_FAILED",
                    "message": f"Failed to create return purchase lines: {str(line_exception)}",
                    "field": "lines",
                }
            ) from line_exception

        # Update Inventory

        try:
            for line_data in lines_data:
                product = line_data["product"]
                quantity = line_data["quantity"]
                decrease_inventory_quantity(
                    product=product,
                    quantity=quantity,
                    warehouse=warehouse,
                )
        except Exception as inventory_exception:
            raise ValidationError(
                {
                    "code": "INVENTORY_UPDATE_FAILED",
                    "message": f"Failed to update inventory: {str(inventory_exception)}",
                    "field": "inventory",
                }
            ) from inventory_exception

        # Recalculate return_purchase order totals

        try:
            return_purchase_order.recalculate_totals()
        except Exception as totals_exception:
            raise ValidationError(
                {
                    "code": "TOTALS_RECALCULATION_FAILED",
                    "message": f"Failed to recalculate return purchase order totals: {str(totals_exception)}",
                    "field": "totals",
                }
            ) from totals_exception

        # Handle Supplier Payment
        print("step 6 validated_data ")
        if supplier_payment_data:
            try:
                create_supplier_payment(
                    uuid=supplier_payment_data.get("uuid"),
                    supplier=supplier_payment_data.get("supplier"),
                    amount=supplier_payment_data.get("amount"),
                    payment_type=PaymentTypes.RETURN_PURCHASE.value,
                    payment_method=supplier_payment_data.get("method"),
                    return_purchase_order=return_purchase_order,
                    note=supplier_payment_data.get("note"),
                    requester=requester,
                )
            except Exception as payment_exception:
                raise ValidationError(
                    {
                        "code": "SUPPLIER_PAYMENT_FAILED",
                        "message": f"Invalid supplier payment: {str(payment_exception)}",
                        "field": "supplier_payment",
                    }
                ) from payment_exception

        print("step 7 validated_data ")
        # Return the created ReturnPurchaseOrder
        return return_purchase_order

    except ValidationError as ve:
        raise ve
    except Exception as e:
        raise ValidationError(
            {
                "code": "RETURN_PURCHASE_ORDER_CREATION_FAILED",
                "message": f"An error occurred during return purchase order creation: {str(e)}",
                "field": "general",
            }
        )


@transaction.atomic
def update_return_purchase_order(requester, return_purchase_order, validated_data):
    try:
        lines_data = validated_data.pop("lines", [])
        warehouse = validated_data.get("warehouse")
        supplier_payment_data = validated_data.pop("supplier_payment", None)
        print(f"return_purchase_order = {return_purchase_order}")
        print(f"validated_data = {validated_data}")
        print(f"supplier_payment_data = {supplier_payment_data}")

        if not warehouse:
            raise ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )

        # Decrease inventory for existing lines
        existing_lines = return_purchase_order.lines.all()
        for line in existing_lines:
            increase_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )

        # Delete existing lines
        existing_lines.delete()

        # Update the order fields
        return_purchase_order.supplier = validated_data.get(
            "supplier", return_purchase_order.supplier
        )
        return_purchase_order.is_received = validated_data.get(
            "is_received", return_purchase_order.is_received
        )
        return_purchase_order.discount_price = validated_data.get(
            "discount_price", return_purchase_order.discount_price
        )
        return_purchase_order.date = validated_data.get(
            "date", return_purchase_order.date
        )
        return_purchase_order.updated_by = requester
        return_purchase_order.save()

        # Create new lines and increase inventory
        for line_data in lines_data:
            line = ReturnPurchaseLine.objects.create(
                return_purchase_order=return_purchase_order, **line_data
            )
            decrease_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )

        # Recalculate totals
        return_purchase_order.recalculate_totals()

        # Update Supplier Payment for the return_purchase order

        supplier_payment = SupplierPayment.objects.filter(
            return_purchase_order__uuid=return_purchase_order.uuid
        ).first()
        print(f"supplier_payment = {supplier_payment}")

        try:
            print(
                f"supplier_payment_data amount = {supplier_payment_data.get('amount')}"
            )
            update_supplier_payment(
                payment_uuid=supplier_payment.uuid,
                supplier=return_purchase_order.supplier,
                new_amount=supplier_payment_data.get("amount"),
                return_purchase_order=return_purchase_order,
                payment_method=supplier_payment_data.get("method"),
                note=supplier_payment_data.get("note"),
                new_payment_type=PaymentTypes.RETURN_PURCHASE.value,
                requester=requester,
            )
        except Exception as payment_exception:
            raise ValidationError(
                {
                    "code": "SUPPLIER_PAYMENT_UPDATE_FAILED",
                    "message": f"Failed to update supplier payment:: {str(payment_exception)}",
                    "field": "supplier_payment",
                }
            ) from payment_exception

        # Return the updated order
        return return_purchase_order

    except ValidationError as ve:
        raise ve
    except Exception as e:
        raise ValidationError(
            {
                "code": "RETURN_PURCHASE_ORDER_UPDATE_FAILED",
                "message": f"An error occurred during return purchase order update: {str(e)}",
                "field": "general",
            }
        )


@transaction.atomic
def delete_return_purchase_order(uuid):
    """
    Service function to handle the deletion of a return purchase order
    while restoring the inventory quantities and marking related payments as deleted.
    """
    # Fetch the order
    return_purchase_order = ReturnPurchaseOrder.objects.get(uuid=uuid, deleted=False)

    # Restore inventory for each line in the order
    for line_data in return_purchase_order.lines.all():
        increase_inventory_quantity(
            product=line_data.product,
            quantity=line_data.quantity,
            warehouse=return_purchase_order.warehouse,
        )

    # Mark related payments as deleted
    related_payments = SupplierPayment.objects.filter(
        return_purchase_order=return_purchase_order, deleted=False
    )
    related_payments.update(deleted=True)

    # Perform a soft delete on the return purchase order
    return_purchase_order.deleted = True
    return_purchase_order.save(update_fields=["deleted"])
