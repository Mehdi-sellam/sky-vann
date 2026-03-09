from django.db import transaction
from typing import Optional
from uuid import UUID
from decimal import Decimal

from core.utils import get_date_in_algeria_timezone

from .models import *
from supplier.models import *
from purchases.models import *
from return_purchases.models import *
from .enum import *
from .utils import *
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from django.db.models.functions import Coalesce
from django.db.models import DateField
from django.db.models.functions import Coalesce, Cast

def get_supplier_payment_list():
    return (
        SupplierPayment.objects.filter(deleted=False)
        .exclude(amount=0)
        .order_by("-created_at")
    )


@transaction.atomic
def create_supplier_payment(
    uuid: UUID,
    supplier: Supplier,
    amount: Decimal,
    payment_type: str,
    payment_method: str,
    note: Optional[str] = None,
    purchase: Optional[PurchaseOrder] = None,
    return_purchase_order: Optional[ReturnPurchaseOrder] = None,
    requester=None,
):
    """
    Create a supplier payment and adjust the supplier's balance accordingly.
    """
    # Ensure valid payment type
    if payment_type not in [item.value for item in PaymentTypes]:
        raise ValueError(
            {
                "code": "invalid_payment_type",
                "message": "Invalid payment type. Must be 'payment' or 'purchase'.",
                "field": "type",
            }
        )
    # Ensure valid payment method
    if payment_method not in [item.value for item in PaymentMethods]:
        raise ValueError(
            {
                "code": "invalid_payment_method",
                "message": "Invalid payment method. Must be 'cash' or 'bank'.",
                "field": "method",
            }
        )

    # Ensure amount is a positive value for payment types
    if Decimal(amount) == Decimal("0.0") and payment_type == PaymentTypes.PAYMENT.value:
        raise ValueError(
            {
                "code": "invalid_amount",
                "message": "Amount must be greater than zero for payments.",
                "field": "amount",
            }
        )

    # Ensure a purchase is specified for purchase payments
    if PaymentTypes.PURCHASE.value == payment_type and not purchase:
        raise ValueError(
            {
                "code": "missing_purchase",
                "message": "A purchase must be specified for a purchase payment.",
                "field": "purchase",
            }
        )

    # Ensure a purchase is specified for purchase payments
    if PaymentTypes.RETURN_PURCHASE.value == payment_type and not return_purchase_order:
        raise ValueError(
            {
                "code": "missing_return_purchase",
                "message": "A return purchase must be specified for a return purchase payment.",
                "field": "purchase",
            }
        )

    old_balance = supplier.balance

    # Create the SupplierPayment record
    payment = SupplierPayment.objects.create(
        uuid=uuid,
        supplier=supplier,
        purchase=purchase,
        return_purchase_order=return_purchase_order,
        old_balance=old_balance,
        amount=Decimal(amount),
        type=payment_type,
        method=payment_method,
        note=note,
        created_by=requester,
    )

    # Recalculate the balance after the payment creation
    payment.new_balance = calculate_supplier_balance(supplier.uuid)
    payment.save(update_fields=["new_balance"])

    return payment


@transaction.atomic
def update_supplier_payment(
    payment_uuid: UUID,
    supplier: Supplier,
    new_amount: Decimal,
    new_payment_type: str,
    payment_method: str,
    note: Optional[str] = None,
    purchase: Optional[PurchaseOrder] = None,
    return_purchase_order: Optional[ReturnPurchaseOrder] = None,
    requester=None,
):
    """
    Update an existing supplier payment and adjust the supplier's balance accordingly.

    """
    # Ensure the new payment type is valid
    if new_payment_type not in [item.value for item in PaymentTypes]:
        raise ValueError(
            {
                "code": "invalid_payment_type",
                "message": "Invalid payment type. Must be 'payment' or 'purchase'.",
                "field": "type",
            }
        )

    # Ensure valid payment method
    if payment_method not in [item.value for item in PaymentMethods]:
        raise ValueError(
            {
                "code": "invalid_payment_method",
                "message": "Invalid payment method. Must be 'cash' or 'bank'.",
                "field": "method",
            }
        )
    # Ensure a purchase is specified for purchase payments
    if PaymentTypes.PURCHASE.value == new_payment_type and not purchase:
        raise ValueError(
            {
                "code": "missing_purchase",
                "message": "A purchase must be specified for a purchase payment.",
                "field": "purchase",
            }
        )

    if (
        PaymentTypes.RETURN_PURCHASE.value == new_payment_type
        and not return_purchase_order
    ):
        raise ValueError(
            {
                "code": "missing_return_purchase",
                "message": "A return purchase must be specified for a return purchase payment.",
                "field": "return_purchase_order",
            }
        )

    try:
        # Fetch the existing payment record
        payment = SupplierPayment.objects.get(uuid=payment_uuid)

        if payment.type != new_payment_type:
            raise ValueError(
                {
                    "code": "invalid_payment_type",
                    "message": "Payment type cannot be changed.",
                    "field": "type",
                }
            )

        # Update the payment record without manually modifying the balance
        payment.amount = new_amount
        payment.type = new_payment_type
        payment.method = payment_method
        payment.purchase = purchase
        payment.return_purchase = return_purchase_order
        payment.note = note
        payment.updated_by = requester
        payment.save()

        # Recalculate the supplier payment balances after updating the payment
        fix_supplier_payment_balances(supplier_uuid=supplier.uuid)

        # Recalculate the balance after updating the payment
        calculate_supplier_balance(supplier_uuid=supplier.uuid)
        return payment

    except SupplierPayment.DoesNotExist:

        raise ValueError(
            {
                "code": "payment_not_found",
                "message": "Payment not found.",
                "field": "uuid",
            }
        )


@transaction.atomic
def delete_supplier_payment(payment_uuid: UUID, supplier: Supplier):
    """
    Soft delete an existing supplier payment and reverse the supplier's balance adjustment.
    """

    try:
        # Fetch the payment record
        payment = SupplierPayment.objects.get(uuid=payment_uuid)

        # Mark the payment as deleted (soft delete)
        payment.deleted = True
        payment.save(update_fields=["deleted"])
        fix_supplier_payment_balances(supplier_uuid=supplier.uuid),
        # Recalculate the balance after deletion
        calculate_supplier_balance(supplier_uuid=supplier.uuid)

    except SupplierPayment.DoesNotExist:
        raise ValueError(
            {
                "code": "payment_not_found",
                "message": "Payment not found.",
                "field": "uuid",
            }
        )


class SupplierStatementService:
    """
    Service class for handling Supplier statement operations
    """

    @staticmethod
    def generate_statement_pdf(supplier, start_date, end_date):
        """
        Generate cliSupplierent statement PDF for a specific supplier
        Returns: HttpResponse with PDF bytes (and headers exposing saved path/URL)
        """

        # 1) Parse period
        period_start, period_end = SupplierStatementService._parse_date_range(
            start_date, end_date
        )

        # 2) Build transactions (ensure proper types)
        result = SupplierStatementService.get_statement_data(
            supplier, period_start, period_end
        )
        # 3) Context for template
        context = {
            "supplier": supplier,
            "period_start": period_start,
            "period_end": period_end,
            "transactions": result.get("transactions", []),
            "total_debits": result.get("total_debits", Decimal("0")),
            "total_credits": result.get("total_credits", Decimal("0")),
            "closing_balance": result.get("closing_balance", Decimal("0")),
            "opening_balance": result.get("opening_balance", Decimal("0")),
            "generation_date": timezone.now(),
            "company": {
                "name": "DJALILOU COM DISTRIBUTION",
                "address": "CITE 38 LOG N 05 CHOUF LEKDAD SETIF",
                "phone": "+213 07 72 92 19 73",
                "email": "",
            },
            "currency": " (DA) ",
        }

        # Import WeasyPrint lazily so environments without its native
        # dependencies can still run the rest of the project and tests.
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "WeasyPrint is required to generate supplier statement PDFs "
                "but could not be imported. Please ensure all native "
                "dependencies are installed."
            ) from exc

        # 4) Render HTML
        html_string = render_to_string("supplier_payments/statement.html", context)

        # base_url helps WeasyPrint resolve relative URLs (images/fonts if you add them later)
        # Use STATIC_ROOT or project BASE_DIR; if you have request, you can use request.build_absolute_uri("/")
        base_url = getattr(settings, "STATIC_ROOT", None) or str(
            getattr(settings, "BASE_DIR")
        )

        # 5) Generate PDF bytes (one time)
        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(
            stylesheets=[]
        )

        # 6) Save to storage (keep a copy)
        safe_name = slugify(supplier.name) or f"Supplier-{supplier.pk}"
        dated = timezone.now().strftime("%Y%m%d-%H%M%S")
        rel_path = f"reports/statements/{supplier.pk}/{safe_name}-{dated}.pdf"
        saved_path = default_storage.save(rel_path, ContentFile(pdf_bytes))

        # 7) Optional: public URL (depends on storage backend)
        try:
            file_url = default_storage.url(saved_path)
        except Exception:
            file_url = None

        # 8) Build the HTTP response (single creation)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="statement_{safe_name}.pdf"'
        )
        response["X-Statement-Path"] = saved_path
        if file_url:
            response["X-Statement-URL"] = file_url

        return response

    @staticmethod
    def get_statement_data(supplier, period_start, period_end):
        """
        Get statement data for a supplier

        Args:
            supplier: supplier instance
            period_start: Start date object
            period_end: End date object

        Returns:
            dict: Statement data
        """
        # Get opening balance
        # Get supplier payments in the period

        supplier_payments = (
            SupplierPayment.objects.filter(
                supplier=supplier,
                deleted=False,
            )
            .annotate(
                effective_date=Coalesce(
                    "purchase__date",
                    "return_purchase_order__date",
                    Cast("created_at", DateField()),
                    output_field=DateField(),
                )
            )
            .filter(effective_date__gte=period_start, effective_date__lte=period_end)
              .select_related("purchase", "return_purchase_order")
            .order_by("effective_date")
        )

        if supplier_payments.exists():
            first_tx = supplier_payments.first()
            opening_balance = first_tx.old_balance or Decimal("0")  # type: ignore
            opening_date = (
                first_tx.effective_date
                if hasattr(first_tx, "effective_date")
                else get_date_in_algeria_timezone(first_tx.created_at)
            )
            last_tx = supplier_payments.last()
            closing_balance = last_tx.new_balance or Decimal("0")

        else:
            # No movements in the window: use initial balance (or compute from history)
            opening_balance = supplier.balance_init or Decimal("0")
            opening_date = period_start
            closing_balance = supplier.balance or Decimal("0")
        # Format transactions
        transactions = SupplierStatementService.format_transaction_data(
            supplier_payments
        )

        if transactions:
            opening_row = {
                "date": opening_date,
                "reference": "-",
                "description": "Solde antérieur",
                "type": "OPENING",
                "method": "-",
                "debit": None,
                "credit": None,
                "balance": opening_balance,
            }
            transactions.insert(0, opening_row)

        # Calculate totals
        total_debits = sum(t["debit"] for t in transactions if t["debit"])
        total_credits = sum(t["credit"] for t in transactions if t["credit"])

        return {
            "transactions": transactions,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "closing_balance": closing_balance,
            "opening_balance": opening_balance,
        }

    @staticmethod
    def _parse_date_range(start_date: str, end_date: str):
        """
        Parse and validate required date range parameters.

        Args:
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format

        Returns:
            tuple[date, date]: (period_start, period_end) as date objects
        """
        try:
            period_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            period_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Les dates doivent être au format YYYY-MM-DD.")

        if period_end < period_start:  # equality is allowed
            raise ValueError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        return period_start, period_end

    @staticmethod
    def _get_transaction_reference(payment):
        """
        Get transaction reference for display

        Args:
            payment: supplierPayment instance

        Returns:
            str: Transaction reference
        """
        if payment.purchase:

            return getattr(payment.purchase, "reference", f"#{payment.purchase.number}")
        elif payment.return_purchase_order:
            return getattr(
                payment.return_purchase_order,
                "reference",
                f"#{payment.return_purchase_order.number}",
            )
        else:
            return "_"

    @staticmethod
    def _get_transaction_description(payment):
        """
        Description standardisée (FR) selon les cas :
        - purchase seule
        - purchase + paiement partiel
        - purchase payée intégralement
        - Retour purchase / Avoir
        - Paiement seul
        - Remboursement fournisseur
        """
        amount = Decimal(getattr(payment, "amount", 0) or 0)
        purchase = getattr(payment, "purchase", None)
        sale_total = getattr(purchase, "total_price", None)
        has_return = getattr(payment, "return_purchase_order", None) is not None
        ptype = getattr(payment, "type", None)

        # --- ACHAT (Bon d'achat n) ---
        if purchase:
            if amount > 0:
                # On distingue "payé intégralement" vs "paiement partiel" si on connaît le total
                if sale_total is not None and amount >= Decimal(sale_total):
                    return "Bon d'achat (payé intégralement)"
                else:
                    return "Bon d'achat  + paiement partiel"
            else:
                return "Bon d'achat "

        # --- RETOUR / AVOIR ---
        if has_return:
            return "Avoir (retour d'achat )"

        # --- PAIEMENT SEUL ---
        try:
            from .enums import PaymentTypes  # adapte l'import si besoin

            if ptype == PaymentTypes.PAYMENT:
                return "Paiement reçu"
            if ptype == PaymentTypes.RETURN_PURCHASE:
                return "Remboursement fournisseur"
        except Exception:
            if ptype == "PAYMENT":
                return "Paiement reçu"
            if ptype == "RETURN_PURCHASE":
                return "Remboursement client"

        # --- Fallback ---
        return "Paiement"

    @staticmethod
    def format_transaction_data(supplier_payments):
        """
        Format supplier payments into transaction format for PDF

        Args:
            supplier_payments: QuerySet of supplierPayment objects
            opening_balance: Decimal opening balance

        Returns:
            list: Formatted transaction data
        """
        transactions = []

        for payment in supplier_payments:
            products = None

            # Get products from purchase order
            if payment.purchase:
                purchase_lines = payment.purchase.lines.filter(deleted=False)
                products = []
                for line in purchase_lines:
                    products.append(
                        {
                            "name": line.product.name,
                            "qty": line.quantity,
                            "unit_price": line.unit_price,
                            "total": line.total_price,
                        }
                    )

            # Get products from return purchase order
            elif payment.return_purchase_order:
                return_lines = payment.return_purchase_order.lines.filter(deleted=False)
                products = []
                for line in return_lines:
                    products.append(
                        {
                            "name": line.product.name,
                            "qty": line.quantity,
                            "unit_price": line.unit_price,
                            "total": line.total_price,
                        }
                    )

            # Determine debit/credit based on payment type
            debit = Decimal("0")
            credit = Decimal("0")
            subtotal = Decimal("0")
            total_discount = Decimal("0")
            grand_total = Decimal("0")
            transaction_date = get_date_in_algeria_timezone(payment.created_at)
            if payment.type == PaymentTypes.PAYMENT.value:  # supplier paying us
                debit = None
                credit = payment.amount

            elif payment.type == PaymentTypes.PURCHASE.value:
                #  purchase or other charges
                debit = payment.purchase.total_price if payment.purchase else None
                credit = payment.amount
                subtotal = payment.purchase.undiscount_price
                total_discount = payment.purchase.discount_price
                grand_total = payment.purchase.total_price
                transaction_date =  payment.purchase.date

            elif (
                payment.type == PaymentTypes.RETURN_PURCHASE.value
            ):  # return_purchase_order or other charges
                credit = (
                    payment.return_purchase_order.total_price
                    if payment.return_purchase_order
                    else None
                )
                debit = payment.amount * -1
                subtotal = payment.return_purchase_order.undiscount_price
                total_discount = payment.return_purchase_order.discount_price
                grand_total = payment.return_purchase_order.total_price
                transaction_date =  payment.return_purchase_order.date
            transactions.append(
                {
                    "date": transaction_date,
                    "reference": SupplierStatementService._get_transaction_reference(
                        payment
                    ),
                    "description": SupplierStatementService._get_transaction_description(
                        payment
                    ),
                    "method": get_payment_method_label_fr(payment.method, credit),
                    "debit": debit,
                    "credit": credit,
                    "balance": payment.new_balance,
                    "products": products,
                    "subtotal": subtotal,
                    "total_discount": total_discount,
                    "grand_total": grand_total,
                }
            )

        return transactions
