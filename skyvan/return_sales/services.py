from django.db import transaction
from .models import *
from warehouse.inventory import *
from customer_payment.services import *
from customer_payment.enum import *
from rest_framework.exceptions import ValidationError, NotFound, APIException
from .error_codes import *
from customer_payment.error_codes import CustomerPaymentErrorCode
from django.db import transaction, IntegrityError, DatabaseError
from customer_payment.models import *
from decimal import Decimal

def get_all_return_sale_orders():
    return ReturnSaleOrder.objects.filter(deleted=False)

def get_return_sale_order_by_uuid(uuid: uuid.UUID) -> ReturnSaleOrder:
    try:
        return_sale_order = ReturnSaleOrder.objects.get(uuid=uuid, deleted=False)
        return return_sale_order
    except ReturnSaleOrder.DoesNotExist:
        raise NotFound(
            {
                "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                "message": f"Return Sale Order with UUID {uuid} not found.",
                "field": "UUID",
            }
        )

def get_return_sale_order_lines(uuid: uuid.UUID):
    sale_order = get_return_sale_order_by_uuid(uuid)
    return sale_order.lines.filter(deleted=False)

def get_return_sale_line_report(request):
    return ReturnSaleLine.objects.filter(
        return_sale_order__deleted=False, deleted=False
    ).order_by("-created_at")


@transaction.atomic
def create_return_sale_order(requester, validated_data):
    date = validated_data.get("date", None)
    warehouse = validated_data.get("warehouse", None)
    
    if not warehouse:
        raise ValidationError(
            {
                "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                "message": "Warehouse not found.",
                "field": "warehouse",
            }
        )

    try:
        return_sale_order = ReturnSaleOrder.objects.create(
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
                "code": ReturnSaleOrderErrorCode.RETURN_SALE_ORDER_CREATION_FAILED.value,
                "message": f"Failed to create return sale order: {str(order_exception)}",
                "field": "return_sale_order",
            }
        )
    lines_data = validated_data.pop("lines", [])

    for line_data in lines_data:
        product = line_data.get("product")
        line_data["cost_price"] = product.cost_price
        line_data["average_cost"] = product.average_cost
        quantity = line_data.get("quantity", Decimal("1"))
        try:
            ReturnSaleLine.objects.create(
            return_sale_order=return_sale_order, **line_data)
        except Exception as line_exception:
            raise ValidationError(
                {
                    "code":  ReturnSaleOrderErrorCode.RETURN_SALE_LINE_CREATION_FAILED.value,
                    "message": f"Failed to create return sale lines: {str(line_exception)}",
                    "field": "lines",
                }
            )

        increase_inventory_quantity(
            product=product,
            quantity=quantity,
            warehouse=warehouse,
        )
    return_sale_order.recalculate_totals()

    customer_payment_data = validated_data.pop("customer_payment", None)

    # Handle Customer Payment
    if customer_payment_data:
        try:
            create_customer_payment(
                uuid=customer_payment_data.get("uuid"),
                customer=customer_payment_data.get("customer"),
                amount=customer_payment_data.get("amount"),
                payment_type=PaymentTypeEnum.RETURN_SALE.value,
                payment_method=customer_payment_data.get("method"),
                return_sale_order=return_sale_order,
                note=customer_payment_data.get("note"),
                requester=requester,
            )
        except Exception as payment_exception:
            raise ValidationError(
                {
                    "code":  CustomerPaymentErrorCode.CUSTOMER_PAYMENT_FAILED.value,
                    "message": f"Invalid customer payment: {str(payment_exception)}",
                    "field": "customer_payment",
                }
            ) 

    return return_sale_order


@transaction.atomic
def update_return_sale_order(requester, return_sale_order, validated_data):
    try:
        lines_data = validated_data.pop("lines", [])
        warehouse = validated_data.get("warehouse")
        customer_payment_data = validated_data.pop("customer_payment", None)

        if not warehouse:
            raise ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )

        # Decrease inventory for existing lines
        existing_lines = return_sale_order.lines.filter(deleted=False)
        for line in existing_lines:
            decrease_inventory_quantity(
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
            line = ReturnSaleLine.objects.create(return_sale_order=return_sale_order,**line_data)
            increase_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )

        return_sale_order.is_received = validated_data.get(
            "is_received", return_sale_order.is_received
        )
        return_sale_order.discount_price = validated_data.get(
            "discount_price", return_sale_order.discount_price
        )            
        return_sale_order.date = validated_data.get("date", return_sale_order.date)
        return_sale_order.updated_by = requester
        return_sale_order.save()            
        # Recalculate totals
        return_sale_order.recalculate_totals()
        
    except Exception as e:
        raise ValidationError(
            {
                "code": ReturnSaleOrderErrorCode.RETURN_SALE_ORDER_UPDATE_FAILED.value,
                "message": f"An error occurred during return sale order update: {str(e)}",
                "field": "general",
            }
        )      
        

        # Update Customer Payment for the return sale order
    try:
        customer_payment = CustomerPayment.objects.filter(
            return_sale_order__uuid=return_sale_order.uuid,deleted=False
        ).first()
        
        update_customer_payment(
            payment_uuid=customer_payment.uuid,
            customer=return_sale_order.customer,
            new_amount=customer_payment_data.get("amount"),
            payment_method=customer_payment_data.get("method"),
            return_sale_order=return_sale_order,
            note=customer_payment_data.get("note"),
            new_payment_type=PaymentTypeEnum.RETURN_SALE.value,
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
    return return_sale_order


@transaction.atomic
def delete_return_sale_order(uuid):
    return_sale_order = get_return_sale_order_by_uuid(uuid)
    warehouse = return_sale_order.warehouse
    
    try:
        lines = return_sale_order.lines.filter(deleted=False)
        for line in  lines:
            decrease_inventory_quantity(
                product=line.product,
                quantity=line.quantity,
                warehouse=warehouse,
            )
        # softe delete lines
        lines.filter(deleted=False).update(deleted=True)
        
        #soft delete return sales order
        return_sale_order.deleted = True
        return_sale_order.save(update_fields=["deleted"])
        #soft delete payment 
        return_sale_order.return_sale_payments.filter(deleted=False).update(deleted=True)
        
        fix_customer_payment_balances(return_sale_order.customer.uuid)
        calculate_customer_balance(return_sale_order.customer.uuid)
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


