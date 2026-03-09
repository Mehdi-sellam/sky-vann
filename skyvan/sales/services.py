from django.db import transaction
from decimal import Decimal

from transfer.utils import decrease_van_inventory_quantity, increase_van_inventory_quantity
from van.services import get_user_van
from .serializers import CreateSaleOrderSerializer
from .models import *
from warehouse.inventory import *
from customer_payment.services import *
from customer_payment.enum import *
from rest_framework.exceptions import ValidationError, NotFound, APIException ,PermissionDenied
from .error_codes import *
from customer_payment.models import *
from customer_payment.error_codes import CustomerPaymentErrorCode
from customer_payment.utils import fix_customer_payment_balances
from django.db import transaction, IntegrityError, DatabaseError
from rest_framework.response import Response
from rest_framework import status

def get_all_sale_orders():
    return SaleOrder.objects.filter(deleted=False)

def get_my_sale_orders(request):
    van = get_user_van(request.user).first()
    if not van:
        raise PermissionDenied("No Van Found.")
    return SaleOrder.objects.filter(deleted=False, van=van, created_by=request.user).order_by("-created_at")

def get_sale_order_by_uuid(uuid: uuid.UUID) -> SaleOrder:
    try:
        sale_order = SaleOrder.objects.get(uuid=uuid, deleted=False)
        return sale_order
    except SaleOrder.DoesNotExist:

        raise NotFound(
            {
                "code": SaleOrderErrorCode.NOT_FOUND.value,
                "message": f"Sale Order with UUID {uuid} not found.",
                "field": "UUID",
            }
        )

def get_sale_order_lines(uuid: uuid.UUID):
    sale_order = get_sale_order_by_uuid(uuid)
    return sale_order.lines.filter(deleted=False)

def get_sale_line_report(request):
    return SaleLine.objects.filter(sale_order__deleted=False,deleted=False).order_by(
        "-created_at"
    )


@transaction.atomic
def create_sale_order(requester, validated_data):
    date = validated_data.get("date", None)
    warehouse = validated_data.pop("warehouse", None)

    if not warehouse:
        raise ValidationError(
            {
                "code": SaleOrderErrorCode.NOT_FOUND.value,
                "message": "Warehouse not found.",
                "field": "warehouse",
            }
        )

    try:
        sale_order = SaleOrder.objects.create(
            uuid=validated_data.get("uuid"),
            customer=validated_data.get("customer"),
            discount_price=validated_data.get("discount_price"),
            is_received=validated_data.get("is_received"),
            warehouse=warehouse,
            date=date,
            created_by=requester,
        )

    except (IntegrityError, DatabaseError) as order_exception:
        raise ValidationError(
            {
                "code": SaleOrderErrorCode.SALE_ORDER_CREATION_FAILED.value,
                "message": f"Failed to create sale order: {str(order_exception)}",
                "field": "sale_order",
            }
        )

        # Extract nested data
    lines_data = validated_data.pop("lines", [])

    for line_data in lines_data:
        product = line_data.get("product")
        line_data["cost_price"] = product.cost_price
        line_data["average_cost"] = product.average_cost
        quantity = line_data.get("quantity", Decimal("1"))
        try:
            SaleLine.objects.create(sale_order=sale_order, **line_data)
        except Exception as line_exception:
            raise ValidationError(
                {
                    "code": SaleOrderErrorCode.SALE_LINE_CREATION_FAILED.value,
                    "message": f"Failed to create sale lines: {str(line_exception)}",
                    "field": "lines",
                }
            )

        decrease_inventory_quantity(
            product=product,
            quantity=quantity,
            warehouse=warehouse,
        )
    sale_order.recalculate_totals()

    customer_payment_data = validated_data.pop("customer_payment", None)

    # Handle Customer Payment
    if customer_payment_data:
        try:
            create_customer_payment(
                uuid=customer_payment_data.get("uuid"),
                customer=sale_order.customer,
                amount=customer_payment_data.get("amount"),
                payment_type=PaymentTypeEnum.SALE.value,
                payment_method=customer_payment_data.get("method"),
                sale=sale_order,
                note=customer_payment_data.get("note"),
                requester=requester,
            )
        except Exception as payment_exception:
            raise ValidationError(
                {
                    "code": CustomerPaymentErrorCode.CUSTOMER_PAYMENT_FAILED.value,
                    "message": f"Invalid customer payment: {str(payment_exception)}",
                    "field": "customer_payment",
                }
            )

    return sale_order


@transaction.atomic
def update_sale_order(requester, sale_order, validated_data):
    try:
        lines_data = validated_data.pop("lines", [])
        warehouse = validated_data.get("warehouse")
        customer_payment_data = validated_data.pop("customer_payment", None)

        if not warehouse:
            raise ValidationError(
                {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )

        # Decrease inventory for existing lines
        existing_lines = sale_order.lines.filter(deleted=False)
        for line in existing_lines:
            increase_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )
            line.deleted = True
            line.save(update_fields=["deleted"])

        for line_data in lines_data:
            product = line_data["product"]
            line_data["cost_price"] = product.cost_price
            line_data["average_cost"] = product.average_cost
            line = SaleLine.objects.create(sale_order=sale_order, **line_data)
            decrease_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )

        sale_order.is_received = validated_data.get(
            "is_received", sale_order.is_received
        )
        sale_order.discount_price = validated_data.get(
            "discount_price", sale_order.discount_price
        )
        sale_order.date = validated_data.get("date", sale_order.date)
        sale_order.updated_by = requester
        sale_order.save()
        # Recalculate totals
        sale_order.recalculate_totals()

    except Exception as e:
        raise ValidationError(
            {
                "code": SaleOrderErrorCode.SALE_ORDER_UPDATE_FAILED.value,
                "message": f"An error occurred during sale order update: {str(e)}",
                "field": "general",
            }
        )

    # Update Customer Payment for the sale order

    try:
        customer_payment = CustomerPayment.objects.filter(
            sale__uuid=sale_order.uuid, deleted=False
        ).first()

        update_customer_payment(
            payment_uuid=customer_payment.uuid,
            customer=sale_order.customer,
            new_amount=customer_payment_data.get("amount"),
            payment_method=customer_payment_data.get("method"),
            sale=sale_order,
            note=customer_payment_data.get("note"),
            new_payment_type=PaymentTypeEnum.SALE.value,
            requester=requester,
        )
    except Exception as payment_exception:
        raise ValidationError(
            {
                "code": CustomerPaymentErrorCode.CUSTOMER_PAYMENT_UPDATE_FAILED.value,
                "message": f"Failed to update customer payment: {str(payment_exception)}",
                "field": "customer_payment",
            }
        )

    # Return the updated order
    return sale_order


@transaction.atomic
def delete_sale_order(uuid: uuid.UUID):
    sale_order = get_sale_order_by_uuid(uuid)
    warehouse = sale_order.warehouse

    try:
        lines = sale_order.lines.filter(deleted=False)
        for line in lines:
            increase_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )

        # softe delete lines
        lines.filter(deleted=False).update(deleted=True)

        # Soft delete sale order
        sale_order.deleted = True
        sale_order.save(update_fields=["deleted"])
        # Soft delete payment
        sale_order.sale_payments.filter(deleted=False).update(deleted=True)

        fix_customer_payment_balances(sale_order.customer.uuid)
        calculate_customer_balance(sale_order.customer.uuid)
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


@transaction.atomic
def create_sale_order_from_van(requester, validated_data):

    van = get_user_van(requester).first()
    if not van:
        raise PermissionDenied("No Van Found.")

    date = validated_data.get("date", None)

    try:
        sale_order = SaleOrder.objects.create(
            uuid=validated_data.get("uuid"),
            customer=validated_data.get("customer"),
            discount_price=validated_data.get("discount_price"),
            is_received=validated_data.get("is_received"),
            van=van, 
            date=date,
            created_by=requester,
        )
    except (IntegrityError, DatabaseError) as order_exception:
        raise ValidationError({
            "code": SaleOrderErrorCode.SALE_ORDER_CREATION_FAILED.value,
            "message": f"Failed to create sale order van: {str(order_exception)}",
            "field": "sale_order_van",
        })

    lines_data = validated_data.pop("lines", [])
    for line_data in lines_data:
        product = line_data.get("product")
        line_data["cost_price"] = product.cost_price
        line_data["average_cost"] = product.average_cost
        quantity = line_data.get("quantity", Decimal("1"))

        try:
            SaleLine.objects.create(sale_order=sale_order, **line_data)
        except Exception as line_exception:
            raise ValidationError({
                "code": SaleOrderErrorCode.SALE_LINE_CREATION_FAILED.value,
                "message": f"Failed to create sale lines: {str(line_exception)}",
                "field": "lines",
            })
        decrease_van_inventory_quantity(
            product=product,
            quantity=quantity,
            van=van,
        )

    sale_order.recalculate_totals()

    customer_payment_data = validated_data.pop("customer_payment", None)
    if customer_payment_data:
        try:
            create_customer_payment(
                uuid=customer_payment_data.get("uuid"),
                customer=sale_order.customer,
                amount=customer_payment_data.get("amount"),
                payment_type=PaymentTypeEnum.SALE.value,
                payment_method=customer_payment_data.get("method"),
                sale=sale_order,
                note=customer_payment_data.get("note"),
                requester=requester,
            )
        except Exception as payment_exception:
            raise ValidationError({
                "code": CustomerPaymentErrorCode.CUSTOMER_PAYMENT_FAILED.value,
                "message": f"Invalid customer payment: {str(payment_exception)}",
                "field": "customer_payment",
            })
    return sale_order

@transaction.atomic
def update_sale_order_from_van(requester, sale_order, validated_data):
    try:
        lines_data = validated_data.pop("lines", [])
        van = validated_data.get("van")
        customer_payment_data = validated_data.pop("customer_payment", None)

        if not van:
            raise ValidationError(
                {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": "Van not found.",
                    "field": "van",
                }
            )

        # Decrease inventory for existing lines
        existing_lines = sale_order.lines.filter(deleted=False)
        for line in existing_lines:
            increase_van_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                van=van,
            )
            line.deleted = True
            line.save(update_fields=["deleted"])

        for line_data in lines_data:
            product = line_data["product"]
            line_data["cost_price"] = product.cost_price
            line_data["average_cost"] = product.average_cost
            line = SaleLine.objects.create(sale_order=sale_order, **line_data)
            decrease_van_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                van=van,
            )

        sale_order.is_received = validated_data.get(
            "is_received", sale_order.is_received
        )
        sale_order.discount_price = validated_data.get(
            "discount_price", sale_order.discount_price
        )
        sale_order.date = validated_data.get("date", sale_order.date)
        sale_order.updated_by = requester
        sale_order.save()
        # Recalculate totals
        sale_order.recalculate_totals()

    except Exception as e:
        raise ValidationError(
            {
                "code": SaleOrderErrorCode.SALE_ORDER_UPDATE_FAILED.value,
                "message": f"An error occurred during sale order update: {str(e)}",
                "field": "general",
            }
        )

    # Update Customer Payment for the sale order

    try:
        customer_payment = CustomerPayment.objects.filter(
            sale__uuid=sale_order.uuid, deleted=False
        ).first()

        update_customer_payment(
            payment_uuid=customer_payment.uuid,
            customer=sale_order.customer,
            new_amount=customer_payment_data.get("amount"),
            payment_method=customer_payment_data.get("method"),
            sale=sale_order,
            note=customer_payment_data.get("note"),
            new_payment_type=PaymentTypeEnum.SALE.value,
            requester=requester,
        )
    except Exception as payment_exception:
        raise ValidationError(
            {
                "code": CustomerPaymentErrorCode.CUSTOMER_PAYMENT_UPDATE_FAILED.value,
                "message": f"Failed to update customer payment: {str(payment_exception)}",
                "field": "customer_payment",
            }
        )

    # Return the updated order
    return sale_order

@transaction.atomic
def delete_sale_order_from_van(uuid: uuid.UUID):
    sale_order = get_sale_order_by_uuid(uuid)
    van = sale_order.van

    try:
        lines = sale_order.lines.filter(deleted=False)
        for line in lines:
            increase_van_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                van=van,
            )

        # softe delete lines
        lines.filter(deleted=False).update(deleted=True)

        # Soft delete sale order
        sale_order.deleted = True
        sale_order.save(update_fields=["deleted"])
        # Soft delete payment
        sale_order.sale_payments.filter(deleted=False).update(deleted=True)

        fix_customer_payment_balances(sale_order.customer.uuid)
        calculate_customer_balance(sale_order.customer.uuid)
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



