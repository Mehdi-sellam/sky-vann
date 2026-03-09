from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Concat
from .models import PurchaseLine, PurchaseOrder, Product
from warehouse.inventory import decrease_inventory_quantity, increase_inventory_quantity
from supplier_payment.services import (
    create_supplier_payment,
    fix_supplier_payment_balances,
    update_supplier_payment,
    calculate_supplier_balance,
)

from rest_framework.exceptions import ValidationError, NotFound, APIException
import uuid
from .error_codes import PurchaseOrderErrorCode
from supplier_payment.models import *
from .utils import calculate_average_cost, recalculate_average_cost
from django.db import transaction, IntegrityError, DatabaseError
from supplier_payment.error_codes import SupplierPaymentErrorCode
from decimal import Decimal


def get_purchase_line_report(request):
    return PurchaseLine.objects.filter(
        purchase_order__deleted=False, deleted=False
    ).order_by("-created_at")


def get_all_purchase_orders():
    return PurchaseOrder.objects.filter(deleted=False).select_related(
        'created_by', 
        'updated_by', 
        'warehouse', 
        'supplier'
    ).annotate(
        created_by__full_name=Concat(   
            'created_by__first_name', Value(' '), 'created_by__last_name'
        ),
        updated_by__full_name=Concat(
            'updated_by__first_name', Value(' '), 'updated_by__last_name'
        )
    )


def get_purchase_order_by_uuid(uuid: uuid.UUID) -> PurchaseOrder:
    try:
        purchase_order = PurchaseOrder.objects.get(uuid=uuid, deleted=False)
        return purchase_order
    except PurchaseOrder.DoesNotExist:

        raise NotFound(
            {
                "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"Purchase Order with UUID {uuid} not found.",
                "field": "UUID",
            }
        )


@transaction.atomic
def create_purchase_order(requester, validated_data):
    warehouse = validated_data.pop("warehouse", None)

    if not warehouse:
        raise ValidationError(
            {
                "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                "message": "Warehouse not found.",
                "field": "warehouse",
            }
        )

    # Create the PurchaseOrder
    try:
        date = validated_data.get("date", None)
        purchase_order = PurchaseOrder.objects.create(
            uuid=validated_data.get("uuid"),
            supplier=validated_data.get("supplier"),
            discount_price=validated_data.get("discount_price"),
            is_received=validated_data.get("is_received"),
            warehouse=warehouse,
            date=date,
            created_by=requester,
        )
    except (IntegrityError, DatabaseError) as order_exception:

        raise ValidationError(
            {
                "code": PurchaseOrderErrorCode.PURCHASE_ORDER_CREATION_FAILED.value,
                "message": f"Failed to create purchase order: {str(order_exception)}",
                "field": "purchase_order",
            }
        )

    lines_data = validated_data.pop("lines", [])
    products_to_update = {}
    for line_data in lines_data:
        product = line_data.get("product")
        if not product:
            raise ValidationError(
                {
                    "code": PurchaseOrderErrorCode.INVALID_PRODUCT.value,
                    "message": "Product is required for purchase lines.",
                    "field": "lines",
                }
            )

        sale_price = line_data.pop("sale_price", product.price)
        unit_price = line_data.get("unit_price", product.cost_price)
        quantity = line_data.get("quantity", Decimal("1"))
        try:
            PurchaseLine.objects.create(
                purchase_order=purchase_order,
                **line_data,
            )
        except Exception as line_exception:

            raise ValidationError(
                {
                    "code": PurchaseOrderErrorCode.PURCHASE_LINE_CREATION_FAILED.value,
                    "message": f"Failed to create purchase lines: {str(line_exception)}",
                    "field": "lines",
                }
            )
        # Batch product updates
        product.average_cost = calculate_average_cost(
            product=product,
            quantity=quantity,
            unit_price=unit_price,
        )
        product.price = sale_price
        product.cost_price = unit_price

        products_to_update[product.uuid] = product

        increase_inventory_quantity(
            product=product,
            quantity=quantity,
            warehouse=warehouse,
        )
    # Save all updated products in one query
    Product.objects.bulk_update(
        products_to_update.values(), ["price", "cost_price", "average_cost"]
    )
    supplier_payment_data = validated_data.pop("supplier_payment", None)

    if supplier_payment_data:
        try:
            create_supplier_payment(
                uuid=supplier_payment_data.get("uuid"),
                supplier=purchase_order.supplier,
                amount=supplier_payment_data.get("amount"),
                payment_type=PaymentTypes.PURCHASE.value,
                payment_method=supplier_payment_data.get("method"),
                purchase=purchase_order,
                note=supplier_payment_data.get("note"),
                requester=requester,
            )
        except Exception as payment_exception:
            raise ValidationError(
                {
                    "code": SupplierPaymentErrorCode.SUPPLIER_PAYMENT_FAILED.value,
                    "message": f"Invalid supplier payment: {str(payment_exception)}",
                    "field": "supplier_payment",
                }
            )
    return purchase_order


@transaction.atomic
def update_purchase_order(requester, purchase_order, validated_data):
    try:
        lines_data = validated_data.pop("lines", [])
        warehouse = validated_data.get("warehouse")
        supplier_payment_data = validated_data.pop("supplier_payment", None)

        if not warehouse:
            raise ValidationError(
                {
                    "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )

        existing_lines = purchase_order.lines.filter(deleted=False)

        for line in existing_lines:
            decrease_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )
            line.deleted = True
            line.save(update_fields=["deleted"])
            # average_cost = recalculate_average_cost(line.product)

            # line.product.average_cost = average_cost
            # line.product.save(update_fields=["average_cost"])

        # Create new lines and increase inventory
        for line_data in lines_data:
            sale_price = line_data.pop("sale_price", Decimal("0"))

            line = PurchaseLine.objects.create(
                purchase_order=purchase_order,
                 **line_data,
            )
            # Adjust inventory
            increase_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )
            # average_cost = recalculate_average_cost(line.product)

            # line.product.average_cost = average_cost
            if sale_price is not None:
                line.product.price = sale_price

            line.product.save(update_fields=["price", "average_cost"])

        # Update the order fields
        purchase_order.is_received = validated_data.get(
            "is_received", purchase_order.is_received
        )
        purchase_order.discount_price = validated_data.get(
            "discount_price", purchase_order.discount_price
        )
        purchase_order.date = validated_data.get("date", purchase_order.date)
        purchase_order.updated_by = requester
        purchase_order.save()
        purchase_order.recalculate_totals()

    except Exception as e:
        raise ValidationError(
            {
                "code": PurchaseOrderErrorCode.PURCHASE_ORDER_UPDATE_FAILED.value,
                "message": f"An error occurred during purchase order update: {str(e)}",
                "field": "general",
            }
        )

    try:
        # Update Supplier Payment for the purchase order
        supplier_payment = SupplierPayment.objects.filter(
            purchase__uuid=purchase_order.uuid, deleted=False
        ).first()
        if supplier_payment != validated_data.get("supplier_payment"):
            update_supplier_payment(
                payment_uuid=supplier_payment.uuid,
                supplier=purchase_order.supplier,
                new_amount=supplier_payment_data.get("amount"),
                purchase=purchase_order,
                payment_method=supplier_payment_data.get("method"),
                note=supplier_payment_data.get("note"),
                new_payment_type=PaymentTypes.PURCHASE.value,
                requester=requester,
            )
    except Exception as payment_exception:
        raise ValidationError(
            {
                "code": SupplierPaymentErrorCode.SUPPLIER_PAYMENT_FAILED.value,
                "message": f"Failed to update supplier payment:: {str(payment_exception)}",
                "field": "supplier_payment",
            }
        )

    return purchase_order


def get_purchase_order_lines(uuid: uuid.UUID):
    purchase_order = get_purchase_order_by_uuid(uuid)
    return purchase_order.lines.filter(deleted=False)


@transaction.atomic
def delete_purchase_order(uuid: uuid.UUID):
    purchase_order = get_purchase_order_by_uuid(uuid)
    warehouse = purchase_order.warehouse
    try:
        product_list = list(
            purchase_order.lines.filter(deleted=False).select_related("product")
        )
        # Soft delete order lines & update inventory
        purchase_order.lines.filter(deleted=False).update(deleted=True)

        for line_data in product_list:
            decrease_inventory_quantity(
                product=line_data.product,
                quantity=line_data.quantity,
                warehouse=warehouse,
            )
        # Soft delete the order
        purchase_order.deleted = True  # Soft delete
        purchase_order.save(update_fields=["deleted"])

        # Batch update product costs
        # products_to_update = []
        # for line_data in product_list:
        #     new_average_cost = recalculate_average_cost(line_data.product)
        #     line_data.product.average_cost = new_average_cost
        #     products_to_update.append(line_data.product)

        # Product.objects.bulk_update(products_to_update, ["average_cost"])
        # delete payments of purchaches

        purchase_order.purchase_payments.filter(deleted=False).update(deleted=True)

        fix_supplier_payment_balances(purchase_order.supplier.uuid)
        calculate_supplier_balance(purchase_order.supplier.uuid)
    except IntegrityError:
        raise APIException(
            {
                "code": "INTEGRITY_ERROR",
                "message": "Database integrity error occurred while deleting the purchase order.",
                "field": "UUID",
            }
        )
    except DatabaseError:
        raise APIException(
            {
                "code": "DATABASE_ERROR",
                "message": "A database error occurred. Please try again.",
                "field": "UUID",
            }
        )
    except Exception as e:
        raise APIException(
            {
                "code": "UNKNOWN_ERROR",
                "message": f"An unexpected error occurred: {str(e)}",
                "field": "UUID",
            }
        )
