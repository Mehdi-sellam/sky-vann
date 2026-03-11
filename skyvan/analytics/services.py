from datetime import datetime, time
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.conf import settings
from django.db.models.functions import Coalesce, NullIf
from django.db.models import (
    Max,
    Min,
    Sum,
    F,
    ExpressionWrapper,
    DecimalField,
    OuterRef,
    Subquery,
    Q,
    Value,
    Exists,
)
from sales.models import SaleOrder, SaleLine
from expense.models import Expense
from decimal import Decimal, ROUND_HALF_UP
from customer.models import Customer
from account.models import User
from supplier.models import Supplier
from purchases.models import PurchaseLine, PurchaseOrder
from warehouse.models import CentralInventory
from product.models import Product
from transfer.models import TransferLine
from van.models import VanAssignment
from return_sales.models import ReturnSaleLine


def round_decimal(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_profit_statistics(date_after=None, date_before=None):

    filters = {}
    filters_sales_line = {}
    if date_before and date_after:
        filters["date__range"] = (date_after, date_before)
        filters_sales_line["sale_order__date__range"] = (
            date_after,
            date_before,
        )
    elif date_before:
        filters["date__lte"] = date_before
        filters_sales_line["sale_order__date__lte"] = date_before
    elif date_after:
        filters["date__gte"] = date_after
        filters_sales_line["sale_order__date__gte"] = date_after

    # Exclude deleted sales orders
    active_sales = SaleOrder.objects.filter(deleted=False, **filters)
    # Calculate total revenue
    total_revenue = Decimal(
        active_sales.aggregate(total=Sum("total_price"))["total"] or "0.0"
    )

    # Exclude deleted sale lines
    active_sale_lines = SaleLine.objects.filter(
        sale_order__deleted=False, deleted=False, **filters_sales_line
    )

    # Step 1: Annotate COGS and COGS using average_cost
    sale_lines = active_sale_lines.annotate(
        cogs=ExpressionWrapper(
            F("quantity") * F("cost_price"), output_field=DecimalField()
        ),
        cogs_value_average_cost=ExpressionWrapper(
            F("quantity") * F("average_cost"), output_field=DecimalField()
        ),
    )

    # Step 2: Aggregate total values in a single query
    cogs_values = sale_lines.aggregate(
        total_cogs=Sum("cogs"),
        total_cogs_average_cost=Sum("cogs_value_average_cost"),
    )

    # Step 3: Extract values safely
    cogs = cogs_values["total_cogs"] or Decimal("0.0")
    cogs_value_average_cost = cogs_values["total_cogs_average_cost"] or Decimal("0.0")
    # Exclude deleted expenses
    active_expenses = Expense.objects.filter(deleted=False, **filters)

    # Calculate total expenses
    total_expenses = active_expenses.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.0"
    )

    # Calculate balances
    client_balances = Customer.objects.filter(deleted=False).aggregate(
        total=Sum("balance")
    )["total"] or Decimal("0.0")
    supplier_balances = Supplier.objects.filter(deleted=False).aggregate(
        total=Sum("balance")
    )["total"] or Decimal("0.0")

    # Compute profits
    gross_profit = total_revenue - cogs_value_average_cost
    net_profit = gross_profit - total_expenses

    profit_margin = Decimal("0.0")
    total_revenue = total_revenue or Decimal("0.0")
    net_profit = net_profit or Decimal("0.0")

    if total_revenue > Decimal("0.0"):
        profit_margin = round((net_profit / total_revenue) * Decimal("100.0"), 2)

    inventory_queryset = CentralInventory.objects.annotate(
        total_cost=ExpressionWrapper(
            F("physical_quantity") * F("product__cost_price"),
            output_field=DecimalField(),
        ),
        total_average_cost=ExpressionWrapper(
            F("physical_quantity") * F("product__average_cost"),
            output_field=DecimalField(),
        ),
    )

    # Step 2: Aggregate after annotation
    inventory_values = inventory_queryset.aggregate(
        total_cost=Sum("total_cost"),
        total_average_cost=Sum("total_average_cost"),
    )

    # Step 3: Extract values safely
    inventory_value_cost = inventory_values["total_cost"] or Decimal("0.0")
    inventory_value_average_cost = inventory_values["total_average_cost"] or Decimal(
        "0.0"
    )

    active_purchases = PurchaseOrder.objects.filter(deleted=False, **filters)
    total_purchases = active_purchases.aggregate(total=Sum("total_price"))[
        "total"
    ] or Decimal("0")

    return {
        "total_revenue": round_decimal(total_revenue),
        "cogs": round_decimal(cogs),
        "cogs_value_average_cost": round_decimal(cogs_value_average_cost),
        "total_expenses": round_decimal(total_expenses),
        "gross_profit": round_decimal(gross_profit),
        "net_profit": round_decimal(net_profit),
        "profit_margin": round_decimal(profit_margin),
        "client_balances": round_decimal(client_balances),  # What clients owe yo)u
        "supplier_balances": round_decimal(
            supplier_balances
        ),  # What you owe supplier)s
        "inventory_value_average_cost": round_decimal(inventory_value_average_cost),
        "inventory_value_cost": round_decimal(inventory_value_cost),
        "total_purchases": round_decimal(total_purchases),
    }




def get_datetime_range_from_query(request):
    start_raw = request.query_params.get("start_date")
    end_raw = request.query_params.get("end_date")

    if not start_raw or not end_raw:
        raise ValidationError({
            "code": "invalid_date_range",
            "message": "start_date and end_date are required (YYYY-MM-DD).",
            "field": "start_end_dates"
        })

    start_d = parse_date(start_raw)
    end_d = parse_date(end_raw)

    if not start_d or not end_d:
        raise ValidationError({
            "code": "invalid_date_format",
            "message": "Use YYYY-MM-DD for start_date and end_date.",
            "field": "start_end_dates"
        })

    if start_d > end_d:
        raise ValidationError({
            "code": "invalid_date_range",
            "message": "start_date cannot be after end_date.",
            "field": "start_end_dates"
        })

    start_dt = timezone.make_aware(datetime.combine(start_d, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_d, time.max))
    return start_dt, end_dt


def get_van_uuid_from_query(user_uuid, request):
    raw_van_uuids = request.query_params.get('van_uuids', '')
    start_dt, end_dt = get_datetime_range_from_query(request)

    if not raw_van_uuids:
        raise ValidationError({
            "code": "missing_value",
            "message": "At least one van_uuid must be provided in query parameters.",
            "field": "van_uuid"
        })
    
    input_uuids = {v.strip() for v in raw_van_uuids.split(',') if v.strip()}
    
    if not input_uuids:
        raise ValidationError({
            "code": "invalid_format",
            "message": "The van_uuids format cannot be empty.",
            "field": "van_uuid"
        })

    valid_uuids_queryset = VanAssignment.objects.filter(
        user__uuid=user_uuid,
        van__uuid__in=input_uuids,
        start_datetime__lt=end_dt,
        end_datetime__gt=start_dt,
        deleted=False
    )

    van_uuids = list(valid_uuids_queryset.values_list('van__uuid', flat=True).distinct())

    valid_uuids = {str(uuid) for uuid in van_uuids}
    
    invalid_uuids = input_uuids - valid_uuids

    if invalid_uuids:
        invalid_list = sorted(list(invalid_uuids))
        raise PermissionDenied(
            f"No valid van assignments found for this user for the following UUIDs: {', '.join(invalid_list)}"
        )

    return valid_uuids, start_dt, end_dt


def get_all_products_statistics(user_uuid, request):
    van_uuids, start_dt, end_dt = get_van_uuid_from_query(user_uuid, request)
    decimal_zero = Value(0, output_field=DecimalField())

    transfer_qs = TransferLine.objects.filter(
        product=OuterRef("pk"),
        deleted=False,
        transfer__deleted=False,
        transfer__created_by__uuid=user_uuid,
        transfer__status="accepted"
    )

    sale_qs = SaleLine.objects.filter(
        product=OuterRef("pk"),
        deleted=False,
        sale_order__deleted=False,
        sale_order__is_received=True,
        sale_order__created_by__uuid=user_uuid,
        sale_order__van__uuid__in=van_uuids
    )

#    return_sale_qs = ReturnSaleLine.objects.filter(
#        product=OuterRef("pk"),
#        deleted=False,
#        return_sale_order__deleted=False,
#        return_sale_order__is_received=True,
#    )
#
#    related_sales_from_vans = SaleOrder.objects.filter(
#        customer=OuterRef("return_sale_order__customer"),
#        van__uuid__in=van_uuids,
#        deleted=False,
#        is_received=True
#    )

    return (
        Product.objects.filter(deleted=False)
        .select_related("category")
        .prefetch_related("barcodes")
        .annotate(
            # OPENING QUANTITY (BEFORE selected start_dt)
            opening_qty_in=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__destination_van__uuid__in=van_uuids,
                    transfer__source_warehouse__isnull=False,
                    transfer__updated_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_out=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_warehouse__isnull=False,
                    transfer__updated_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_van_to_van_in=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__destination_van__uuid__in=van_uuids,
                    transfer__source_van__isnull=False,
                    transfer__updated_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_van_to_van_out=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_van__isnull=False,
                    transfer__updated_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_sold=Coalesce(Subquery(
                sale_qs.filter(
                    sale_order__created_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_returned=decimal_zero
        )
        .annotate(
            opening_quantity=ExpressionWrapper(
                (F("opening_qty_in") + F("opening_qty_van_to_van_in") + F("opening_qty_returned")) - 
                (F("opening_qty_out") + F("opening_qty_van_to_van_out") + F("opening_qty_sold")),
                output_field=DecimalField()
            )
        )
        .annotate(
            quantity_transfered_warehouse_to_van=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__destination_van__uuid__in=van_uuids,
                    transfer__source_warehouse__isnull=False,
                    transfer__updated_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_transfered_van_to_warehouse=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_warehouse__isnull=False,
                    transfer__updated_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_transfered_van_to_van_in=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__destination_van__uuid__in=van_uuids,
                    transfer__source_van__isnull=False,
                    transfer__updated_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_transfered_van_to_van_out=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_van__isnull=False,
                    transfer__updated_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_sold=Coalesce(Subquery(
                sale_qs.filter(
                    sale_order__created_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_returned_sale=decimal_zero,
        )
        .annotate(
            # Opening Stock + Stock In + Stock returned - Stock Out - Stock Sold
            remaining_quantity=ExpressionWrapper(
                (F("opening_quantity") + F("quantity_transfered_warehouse_to_van") + F("quantity_returned_sale") + F("quantity_transfered_van_to_van_in")) - 
                (F("quantity_transfered_van_to_warehouse") + F("quantity_sold") + F("quantity_transfered_van_to_van_out")),
                output_field=DecimalField()
            )
        )
        .filter(
            Q(opening_quantity__gt=0) |
            Q(opening_quantity__lt=0) |
            Q(quantity_transfered_warehouse_to_van__gt=0) |
            Q(quantity_transfered_van_to_warehouse__gt=0) |
            Q(quantity_transfered_van_to_van_in__gt=0) |
            Q(quantity_transfered_van_to_van_out__gt=0) |
            Q(quantity_sold__gt=0) |
            Q(quantity_returned_sale__gt=0) |
            Q(remaining_quantity__gt=0) |
            Q(remaining_quantity__lt=0)
        )
        .order_by("name")
    )


def get_most_sold_products(request):
    ''' 
    get the quantity sold - returns sum of products sold from 
    a van and sort them by quantity sold

    '''
    decimal_zero = Value(0, output_field=DecimalField())

    sales_qs = SaleLine.objects.filter(
        product=OuterRef("pk"),
        deleted=False,
        sale_order__deleted=False,
        sale_order__is_received=True
    ).values("product").annotate(total=Sum("quantity")).values("total")

    returns_qs = ReturnSaleLine.objects.filter(
        product=OuterRef("pk"),
        deleted=False,
        return_sale_order__deleted=False,
        return_sale_order__is_received=True
    ).values("product").annotate(total=Sum("quantity")).values("total")

    return (
        Product.objects.filter(deleted=False,)
        .select_related("category")
        .prefetch_related("barcodes")
        .annotate(
            gross_sold=Coalesce(Subquery(sales_qs), decimal_zero),
            total_returned=Coalesce(Subquery(returns_qs), decimal_zero)
        )
        .annotate(
            quantity_sold=ExpressionWrapper(
                F("gross_sold") - F("total_returned"),
                output_field=DecimalField()
            )
        )
        .filter(quantity_sold__gt=0)
        .order_by("-quantity_sold", "name")
    )



def get_sorted_net_revenue_per_product():
    ''' 
    get the quantity sum and the total_price sum 
    (net revenue) of a sold product from a van and 
    calculate its the avg_unit_price and sort them 
    by product net_revenue and name

    '''
    return (
        Product.objects.filter(
            deleted=False,
            sale_lines__deleted=False,
            sale_lines__sale_order__deleted=False
        )
        .select_related("category")
        .prefetch_related("barcodes")
        .annotate(
            quantity_sold=Sum("sale_lines__quantity"),
            net_revenue=Sum("sale_lines__total_price"),
        )
        .filter(quantity_sold__gt=0)
        .annotate(
            # weighted average NET unit price
            # NullIf is a safety net: if quantity_sold is 0, it returns NULL instead of crashing
            avg_unit_price=ExpressionWrapper(
                F("net_revenue") / NullIf(F("quantity_sold"), Value(0)), 
                output_field=DecimalField(
                    max_digits=settings.DEFAULT_MAX_DIGITS,
                    decimal_places=settings.DEFAULT_DECIMAL_PLACES,
                )
            )
        )
        .order_by("-net_revenue", "name")
    )




def get_sorted_products_by_profit():
    """ 
    Calculates profit by product using the snapshot 'average_cost' on SaleLines and returns.
    This is the standard accounting method for Cost of Goods Sold (COGS).
    """
    decimal_out = DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )

    decimal_zero = Value(0, output_field=decimal_out)

    sales_base = SaleLine.objects.filter(
        product=OuterRef("pk"), deleted=False, 
        sale_order__deleted=False, sale_order__is_received=True
    )
    returns_base = ReturnSaleLine.objects.filter(
        product=OuterRef("pk"), deleted=False, 
        return_sale_order__deleted=False, return_sale_order__is_received=True
    )

    return (
        Product.objects.filter(
            deleted=False,
            sale_lines__deleted=False,
            sale_lines__sale_order__deleted=False
        )
        .select_related("category")
        .prefetch_related("barcodes")
        .annotate(
            # Gross totals
            gross_qty=Coalesce(Subquery(sales_base.values("product").annotate(t=Sum("quantity")).values("t")), decimal_zero),
            gross_rev=Coalesce(Subquery(sales_base.values("product").annotate(t=Sum("total_price")).values("t")), decimal_zero),
            gross_cogs=Coalesce(Subquery(sales_base.values("product").annotate(t=Sum(F("quantity") * F("average_cost"))).values("t")), decimal_zero),

            # returns
            ret_qty=Coalesce(Subquery(returns_base.values("product").annotate(t=Sum("quantity")).values("t")), decimal_zero),
            ret_rev=Coalesce(Subquery(returns_base.values("product").annotate(t=Sum("total_price")).values("t")), decimal_zero),
            ret_cogs=Coalesce(Subquery(returns_base.values("product").annotate(t=Sum(F("quantity") * F("average_cost"))).values("t")), decimal_zero),
        )
        .annotate(
            quantity_sold=ExpressionWrapper(F("gross_qty") - F("ret_qty"), output_field=decimal_out),
            net_revenue=ExpressionWrapper(F("gross_rev") - F("ret_rev"), output_field=decimal_out),
            # Cost of Goods Sold (COGS)
            total_cost_value=ExpressionWrapper(F("gross_cogs") - F("ret_cogs"), output_field=decimal_out),
        )
        .filter(Q(gross_qty__gt=0) | Q(ret_qty__gt=0))
        .annotate(
            profit=ExpressionWrapper(
                F("net_revenue") - F("total_cost_value"), 
                output_field=decimal_out
            ),
            # (Average unit cost of items sold)
            avg_unit_cost_price=ExpressionWrapper(
                F("total_cost_value") / NullIf(F("quantity_sold"), Value(0)),
                output_field=decimal_out
            )
        )
        .filter(quantity_sold__gt=0)
        .order_by("-profit", "name")
    )
