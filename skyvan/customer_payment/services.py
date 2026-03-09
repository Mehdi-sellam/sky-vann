from django.db import transaction
from typing import Optional
from uuid import UUID
from decimal import Decimal

from core.utils import get_date_in_algeria_timezone
from .models import CustomerPayment
from customer.models import Customer
from sales.models import SaleOrder
from return_sales.models import ReturnSaleOrder
from .enum import *
from .utils import *
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime

from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q, F
from django.db.models.functions import Coalesce
from django.db.models import DateField
from django.db.models.functions import Coalesce, Cast

from django.utils import timezone





def get_status():
    return CustomerPayment.objects.filter(deleted=False).order_by("-created_at")


def get_customer_payments_list():
    return (
        CustomerPayment.objects.filter(deleted=False)
        .exclude(amount=0)
        .order_by("-created_at")
    )


@transaction.atomic
def create_customer_payment(
    uuid: UUID,
    customer: Customer,
    amount: Decimal,
    payment_type: str,
    payment_method: str,
    note: Optional[str] = None,
    sale: Optional[SaleOrder] = None,
    return_sale_order: Optional[ReturnSaleOrder] = None,
    requester=None,
):
    """
    Create a customer payment and adjust the customer's balance accordingly.
    """

    # Ensure valid payment type
    if payment_type not in [item.value for item in PaymentTypeEnum]:
        raise ValueError(
            {
                "code": "invalid_payment_type",
                "message": "Invalid payment type. Must be 'payment' or 'sale'.",
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
    if (
        Decimal(amount) == Decimal("0.0")
        and payment_type == PaymentTypeEnum.PAYMENT.value
    ):
        raise ValueError(
            {
                "code": "invalid_amount",
                "message": "Amount must be greater than zero for payments.",
                "field": "amount",
            }
        )

    # Ensure a sale is specified for sale payments
    if PaymentTypeEnum.SALE.value == payment_type and not sale:
        raise ValueError(
            {
                "code": "missing_sale",
                "message": "A  sale must be specified for a sale payment. or type",
                "field": "sale||type",
            }
        )

    if PaymentTypeEnum.RETURN_SALE.value == payment_type and not return_sale_order:
        raise ValueError(
            {
                "code": "missing_return_sale",
                "message": "A return sale must be specified for a return sale payment. or type",
                "field": "return_sale_order||type",
            }
        )

    old_balance = customer.balance

    # Create the CustomerPayment record
    payment = CustomerPayment.objects.create(
        uuid=uuid,
        customer=customer,
        sale=sale,
        return_sale_order=return_sale_order,
        old_balance=old_balance,
        amount=Decimal(amount),
        type=payment_type,
        method=payment_method,
        note=note,
        created_by=requester,
    )

    payment.new_balance = calculate_customer_balance(customer.uuid)
    payment.save(update_fields=["new_balance"])

    return payment


@transaction.atomic
def update_customer_payment(
    payment_uuid: UUID,
    customer: Customer,
    new_amount: Decimal,
    new_payment_type: str,
    payment_method: str,
    note: Optional[str] = None,
    sale: Optional[SaleOrder] = None,
    return_sale_order: Optional[ReturnSaleOrder] = None,
    requester=None,
):
    """
    Update an existing customer payment and adjust the customer's balance accordingly.
    """

    # Ensure the new payment type is valid
    if new_payment_type not in [item.value for item in PaymentTypeEnum]:
        raise ValueError(
            {
                "code": "invalid_payment_type",
                "message": "Invalid payment type. Must be 'payment' or 'sale'.",
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

    # Ensure a sale is specified for sale payments
    if PaymentTypeEnum.SALE.value == new_payment_type and not sale:
        raise ValueError(
            {
                "code": "missing_sale",
                "message": "A sale must be specified for a sale payment.",
                "field": "sale",
            }
        )

    if PaymentTypeEnum.RETURN_SALE.value == new_payment_type and not return_sale_order:
        raise ValueError(
            {
                "code": "missing_return_sale",
                "message": "A return sale must be specified for a return sale payment.",
                "field": "return_sale_order",
            }
        )
    try:
        # Fetch the existing payment record
        payment = CustomerPayment.objects.get(uuid=payment_uuid)
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
        payment.sale = sale
        payment.return_sale_order = return_sale_order
        payment.note = note
        payment.updated_by = requester
        payment.save()

        # Recalculate the customer payment balances after updating the payment
        fix_customer_payment_balances(customer_uuid=customer.uuid),
        # Recalculate the balance after updating the payment
        # TO DO REMOVE THIS
        calculate_customer_balance(customer_uuid=customer.uuid)

        return payment

    except CustomerPayment.DoesNotExist:
        raise ValueError(
            {
                "code": "payment_not_found",
                "message": "Payment not found.",
                "field": "uuid",
            }
        )


@transaction.atomic
def delete_customer_payment(payment_uuid: UUID, customer: Customer):
    """
    Soft delete an existing customer payment and reverse the customer's balance adjustment.
    """
    try:
        # Fetch the payment record
        payment = CustomerPayment.objects.get(uuid=payment_uuid)

        # Mark the payment as deleted (soft delete)
        payment.deleted = True
        payment.save(update_fields=["deleted"])

        fix_customer_payment_balances(customer_uuid=customer.uuid)
        # Recalculate the balance after deletion
        calculate_customer_balance(customer_uuid=customer.uuid)

    except CustomerPayment.DoesNotExist:
        raise ValueError(
            {
                "code": "payment_not_found",
                "message": "Payment not found.",
                "field": "uuid",
            }
        )


class ClientStatementService:
    """
    Service class for handling client statement operations
    """

    @staticmethod
    def generate_statement_pdf(customer, start_date, end_date):
        """
        Generate client statement PDF for a specific customer
        Returns: HttpResponse with PDF bytes (and headers exposing saved path/URL)
        """

        # 1) Parse period
        period_start, period_end = ClientStatementService._parse_date_range(
            start_date, end_date
        )

        # 2) Build transactions (ensure proper types)
        result = ClientStatementService.get_statement_data(
            customer, period_start, period_end
        )
        # 3) Context for template
        context = {
            "customer": customer,
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
                "WeasyPrint is required to generate customer statement PDFs "
                "but could not be imported. Please ensure all native "
                "dependencies are installed."
            ) from exc

        # 4) Render HTML
        html_string = render_to_string("customer_payments/statement.html", context)

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
        safe_name = slugify(customer.name) or f"customer-{customer.pk}"
        dated = timezone.now().strftime("%Y%m%d-%H%M%S")
        rel_path = f"reports/statements/{customer.pk}/{safe_name}-{dated}.pdf"
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
    def get_statement_data(customer, period_start, period_end):
        """
        Get statement data for a customer

        Args:
            customer: Customer instance
            period_start: Start date object
            period_end: End date object

        Returns:
            dict: Statement data
        """
        # Get opening balance
        # Get customer payments in the period
        customer_payments = (
            CustomerPayment.objects.filter(
                customer=customer,
                deleted=False,
            )
            .annotate(
                effective_date=Coalesce(
                    "sale__date",
                    "return_sale_order__date",
                    Cast("created_at", DateField()),
                    output_field=DateField(),
                )
            )
            .filter(effective_date__gte=period_start, effective_date__lte=period_end)
            .select_related("sale", "return_sale_order")
            .order_by("effective_date")
        )

        if customer_payments.exists():
            first_tx = customer_payments.first()
            opening_balance = first_tx.old_balance or Decimal("0")  # type: ignore
            opening_date = (
                first_tx.effective_date
                if hasattr(first_tx, "effective_date")
                else get_date_in_algeria_timezone(first_tx.created_at)
            )

            last_tx = customer_payments.last()
            closing_balance = last_tx.new_balance or Decimal("0")

        else:
            # No movements in the window: use initial balance (or compute from history)
            opening_balance = customer.balance_init or Decimal("0")
            opening_date = period_start
            closing_balance = customer.balance or Decimal("0")
        # Format transactions
        transactions = ClientStatementService.format_transaction_data(customer_payments)

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
            payment: CustomerPayment instance

        Returns:
            str: Transaction reference
        """
        if payment.sale:
            # TODO: Adjust field name based on your actual model
            return getattr(payment.sale, "reference", f"#{payment.sale.number}")
        elif payment.return_sale_order:
            # TODO: Adjust field name based on your actual model
            return getattr(
                payment.return_sale_order,
                "reference",
                f"#{payment.return_sale_order.number}",
            )
        else:
            return "_"

    @staticmethod
    def _get_transaction_description(payment):
        """
        Description standardisée (FR) selon les cas :
        - Vente seule
        - Vente + paiement partiel
        - Vente payée intégralement
        - Retour / Avoir
        - Paiement seul
        - Remboursement client
        """
        amount = Decimal(getattr(payment, "amount", 0) or 0)
        sale = getattr(payment, "sale", None)
        sale_total = getattr(sale, "total_price", None)
        has_return = getattr(payment, "return_sale_order", None) is not None
        ptype = getattr(payment, "type", None)

        # --- VENTE (Bon de livraison) ---
        if sale:
            if amount > 0:
                # On distingue "payé intégralement" vs "paiement partiel" si on connaît le total
                if sale_total is not None and amount >= Decimal(sale_total):
                    return "Bon de livraison (payé intégralement)"
                else:
                    return "Bon de livraison + paiement partiel"
            else:
                return "Bon de livraison"

        # --- RETOUR / AVOIR ---
        if has_return:
            return "Avoir (retour de vente)"

        # --- PAIEMENT SEUL ---
        try:
            from .enums import PaymentTypeEnum  # adapte l'import si besoin

            if ptype == PaymentTypeEnum.PAYMENT:
                return "Paiement reçu"
            if ptype == PaymentTypeEnum.RETURN_SALE:
                return "Remboursement client"
        except Exception:
            if ptype == "PAYMENT":
                return "Paiement reçu"
            if ptype == "RETURN_SALE":
                return "Remboursement client"

        # --- Fallback ---
        return "Paiement"

    @staticmethod
    def format_transaction_data(customer_payments):
        """
        Format customer payments into transaction format for PDF

        Args:
            customer_payments: QuerySet of CustomerPayment objects
            opening_balance: Decimal opening balance

        Returns:
            list: Formatted transaction data
        """
        transactions = []

        for payment in customer_payments:
            products = None

            # Get products from sale order
            if payment.sale:
                sale_lines = payment.sale.lines.filter(deleted=False)
                products = []
                for line in sale_lines:
                    products.append(
                        {
                            "name": line.product.name,
                            "qty": line.quantity,
                            "unit_price": line.unit_price,
                            "total": line.total_price,
                        }
                    )

            # Get products from return sale order
            elif payment.return_sale_order:
                return_lines = payment.return_sale_order.lines.filter(deleted=False)
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
            if payment.type == PaymentTypeEnum.PAYMENT.value:  # Customer paying us
                debit = None
                credit = payment.amount

            elif payment.type == PaymentTypeEnum.SALE.value:
                #  Sale or other charges
                debit = payment.sale.total_price if payment.sale else None
                credit = payment.amount
                subtotal = payment.sale.undiscount_price
                total_discount = payment.sale.discount_price
                grand_total = payment.sale.total_price
                transaction_date = payment.sale.date
            elif (
                payment.type == PaymentTypeEnum.RETURN_SALE.value
            ):  # Sale or other charges
                credit = (
                    payment.return_sale_order.total_price
                    if payment.return_sale_order
                    else None
                )
                debit = payment.amount * -1
                subtotal = payment.return_sale_order.undiscount_price
                total_discount = payment.return_sale_order.discount_price
                grand_total = payment.return_sale_order.total_price
                transaction_date = payment.return_sale_order.date
            transactions.append(
                {
                    "date": transaction_date,
                    "reference": ClientStatementService._get_transaction_reference(
                        payment
                    ),
                    "description": ClientStatementService._get_transaction_description(
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
