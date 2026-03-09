from django.db.models import Sum
from decimal import Decimal
from return_purchases.models import ReturnPurchaseOrder
from supplier_payment.enum import PaymentTypes
from supplier.models import Supplier
from purchases.models import PurchaseOrder
from .models import SupplierPayment
from uuid import UUID
from .enum import PaymentMethods


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


def calculate_supplier_balance(supplier_uuid: UUID) -> Decimal:

    supplier = Supplier.objects.get(uuid=supplier_uuid)
    initial_balance = supplier.balance_init

    # Get total payments related to the supplier (both payment and purchase type)
    total_payments = SupplierPayment.objects.filter(
        supplier__uuid=supplier_uuid, deleted=False
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.0")

    # Get total purchases related to the supplier
    total_purchases = PurchaseOrder.objects.filter(
        supplier__uuid=supplier_uuid, deleted=False
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.0")
    # Get total purchases related to the supplier
    total_return_purchases = ReturnPurchaseOrder.objects.filter(
        supplier__uuid=supplier_uuid, deleted=False
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.0")
    # Calculate the balance: initial_balance + total_payments - total_purchases
    balance = (
        initial_balance + (total_purchases - total_return_purchases)
    ) - total_payments

    # Update the supplier's balance in the database
    supplier.balance = balance
    supplier.save()  # Save the updated balance to the supplier record

    return balance


def fix_supplier_payment_balances(supplier_uuid: UUID):

    # Fetch the supplier and initialize balance
    supplier = Supplier.objects.get(uuid=supplier_uuid, deleted=False)
    current_balance = supplier.balance_init

    # Fetch all payments for the supplier, ordered by creation time
    payments = SupplierPayment.objects.filter(
        supplier__uuid=supplier_uuid, deleted=False
    ).order_by("created_at")

    # Update each payment record
    for payment in payments:
        # Set the old balance before this payment
        payment.old_balance = current_balance

        if payment.type == PaymentTypes.PAYMENT.value:
            # Direct payment increases the balance
            current_balance -= payment.amount

        elif payment.type == PaymentTypes.PURCHASE.value and payment.purchase:
            # Adjust balance by the difference between purchase price and payment
            net_purchase_adjustment = payment.purchase.total_price - payment.amount
            current_balance += net_purchase_adjustment

        elif (
            payment.type == PaymentTypes.RETURN_PURCHASE.value
            and payment.return_purchase_order
        ):
            # Adjust balance by the difference between return sale price and payment
            net_return_purchase_adjustment = (
                payment.return_purchase_order.total_price + payment.amount
            )
            current_balance -= net_return_purchase_adjustment

        # Set the new balance after applying the payment adjustment
        payment.new_balance = current_balance

        # Save the updated payment record
        payment.save(update_fields=["old_balance", "new_balance"])
