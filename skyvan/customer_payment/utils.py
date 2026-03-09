from django.db.models import Sum
from decimal import Decimal
from customer.models import Customer
from sales.models import SaleOrder
from customer_payment.enum import PaymentTypeEnum
from return_sales.models import ReturnSaleOrder
from .models import CustomerPayment
from uuid import UUID
from customer_payment.enum import PaymentMethods


def get_payment_method_label_fr(value: str, credit=None) -> str:
    """Return the French label for a payment method value."""
    if credit is None or (
        isinstance(credit, (int, float, Decimal)) and Decimal(credit) == 0
    ):
        return "-"
    mapping = {
        PaymentMethods.CASH.value: "Espèces",
        PaymentMethods.CARD.value: "Carte interbancaire (CIB)",
        PaymentMethods.CHEQUE.value: "Chèque bancaire",
        PaymentMethods.BANK_TRANSFER.value: "Virement bancaire",
    }
    return mapping.get(value, value)


def calculate_customer_balance(customer_uuid: UUID) -> Decimal:

    # Get the customer's initial balance (if applicable)
    customer = Customer.objects.get(uuid=customer_uuid)
    initial_balance = customer.balance_init

    # Get total payments related to the customer (both payment and sale type)
    total_payments = CustomerPayment.objects.filter(
        customer__uuid=customer_uuid, deleted=False
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.0")

    # Get total sales related to the customer
    total_sales = SaleOrder.objects.filter(
        customer__uuid=customer_uuid, deleted=False
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.0")

    total_return_sales = ReturnSaleOrder.objects.filter(
        customer__uuid=customer_uuid, deleted=False
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.0")

    # Calculate the balance:
    balance = (initial_balance + (total_sales - total_return_sales)) - total_payments

    # Update the customer's balance in the database
    customer.balance = balance
    customer.save()  # Save the updated balance to the customer record

    return balance


def fix_customer_payment_balances(customer_uuid: UUID):

    # Fetch the customer and initialize balance
    customer = Customer.objects.get(uuid=customer_uuid)
    current_balance = customer.balance_init

    # Fetch all payments for the customer, ordered by creation time
    payments = CustomerPayment.objects.filter(
        customer__uuid=customer_uuid, deleted=False
    ).order_by("created_at")

    # Update each payment record
    for payment in payments:
        # Set the old balance before this payment
        payment.old_balance = current_balance

        if payment.type == PaymentTypeEnum.PAYMENT.value:
            # Direct payment increases the balance
            current_balance -= payment.amount

        elif payment.type == PaymentTypeEnum.SALE.value and payment.sale:
            # Adjust balance by the difference between sale price and payment
            net_sale_adjustment = payment.sale.total_price - payment.amount
            current_balance += net_sale_adjustment

        elif (
            payment.type == PaymentTypeEnum.RETURN_SALE.value
            and payment.return_sale_order
        ):
            # Adjust balance by the difference between return sale price and payment
            net_return_sale_adjustment = (
                payment.return_sale_order.total_price + payment.amount
            )
            current_balance -= net_return_sale_adjustment

        # Set the new balance after applying the payment adjustment
        payment.new_balance = current_balance

        # Save the updated payment record
        payment.save(update_fields=["old_balance", "new_balance"])
