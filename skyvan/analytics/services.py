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
from return_sales.models import ReturnSaleLine
from supplier.models import Supplier
from purchases.models import PurchaseLine, PurchaseOrder
from warehouse.models import CentralInventory
from product.models import Product
from transfer.models import TransferLine
from van.models import VanAssignment


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
        raise ValidationError({"van_uuid": "At least one van_uuid must be provided."})
    
    input_uuids = {v.strip() for v in raw_van_uuids.split(',') if v.strip()}
    
    # Filter assignments that overlap with the requested date range
    assignments = VanAssignment.objects.filter(
        user__uuid=user_uuid,
        van__uuid__in=input_uuids,
        start_datetime__lt=end_dt,  # Assignment started before request ended
        end_datetime__gt=start_dt,  # Assignment ended after request started
        deleted=False
    )

    if not assignments.exists():
        raise PermissionDenied("No valid van assignments found for the selected period.")

# 1. Correctly extract UUIDs
    valid_uuids = list(assignments.values_list('van__uuid', flat=True).distinct())
    
    # 2. Correctly aggregate the bounding dates
    bounds = assignments.aggregate(
        actual_min=Min('start_datetime'),
        actual_max=Max('end_datetime')
    )

    # 3. Intersect the requested range with the assignment range
    final_start = max(bounds['actual_min'], start_dt)
    final_end = min(bounds['actual_max'], end_dt)
    print(final_start, final_end)

    return valid_uuids, final_start, final_end


def get_all_products_statistics(user_uuid, request):

    van_uuids, start_dt, end_dt= get_van_uuid_from_query(user_uuid, request)
    print(start_dt, end_dt)
    decimal_zero = Value(0, output_field=DecimalField())

    transfer_qs = TransferLine.objects.filter(
        product=OuterRef("pk"),
        deleted=False,
        transfer__deleted=False,
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

#    related_sales = sale_qs.filter(
#        sale_order__customer=OuterRef("return_sale_order__customer"),
#        sale_order__van__uuid__in=van_uuids
#    )

    # TOTAL RETURNS (Customer -> Warehouse/Van)
#    returns_total = ReturnSaleLine.objects.filter(
#        product=OuterRef("pk"),
#        deleted=False,
#        return_sale_order__deleted=False,
#        return_sale_order__is_received=True,
#        return_sale_order__created_at__range=(start_dt, end_dt),
#    ).filter(Exists(related_sales)).order_by().values("product").annotate(total=Sum("quantity")).values("total")

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
                    transfer__created_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_out=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_warehouse__isnull=False,
                    transfer__created_by__uuid=user_uuid,
                    transfer__created_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            opening_qty_sold=Coalesce(Subquery(
                sale_qs.filter(
                    sale_order__created_by__uuid=user_uuid,
                    sale_order__created_at__lt=start_dt
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),
        )
        .annotate(
            opening_quantity=ExpressionWrapper(
                F("opening_qty_in") - (F("opening_qty_out") + F("opening_qty_sold")),
                output_field=DecimalField()
            )
        )
        .annotate(
            quantity_transfered_warehouse_to_van=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__destination_van__uuid__in=van_uuids,
                    transfer__source_warehouse__isnull=False,
                    transfer__created_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_transfered_van_to_warehouse=Coalesce(Subquery(
                transfer_qs.filter(
                    transfer__source_van__uuid__in=van_uuids,
                    transfer__destination_warehouse__isnull=False,
                    transfer__created_by__uuid=user_uuid,
                    transfer__created_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_sold=Coalesce(Subquery(
                sale_qs.filter(
                    sale_order__created_by__uuid=user_uuid,
                    sale_order__created_at__range=(start_dt, end_dt)
                ).values("product").annotate(total=Sum("quantity")).values("total")
            ), decimal_zero),

            quantity_returned_sale=decimal_zero,
        )
        .annotate(
            # Opening Stock + Stock In + Stock returned - Stock Out - Stock Sold
            remaining_quantity=ExpressionWrapper(
                (F("opening_quantity") + F("quantity_transfered_warehouse_to_van") + F("quantity_returned_sale")) - 
                (F("quantity_transfered_van_to_warehouse") + F("quantity_sold")),
                output_field=DecimalField()
            )
        )
        .filter(
            Q(opening_quantity__gt=0) |
            Q(quantity_transfered_warehouse_to_van__gt=0) |
            Q(quantity_transfered_van_to_warehouse__gt=0) |
            Q(quantity_sold__gt=0)
        )
        .order_by("name")
    )


def get_most_sold_products(request):
    ''' 
    get the quantity sold sum of products sold from 
    a van and sort them by quantity sold

    '''
    start_date, end_date = get_datetime_range_from_query(request)

    return (
        Product.objects.filter(
            deleted=False,
            sale_lines__deleted=False,
            sale_lines__sale_order__deleted=False,
            sale_lines__sale_order__created_at__range=(start_date, end_date)
        )
        .select_related("category")
        .prefetch_related("barcodes")
        .annotate(
            quantity_sold=Sum("sale_lines__quantity")
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
    Calculates profit by product using the snapshot 'average_cost' on SaleLines.
    This is the standard accounting method for Cost of Goods Sold (COGS).
    """
    decimal_out = DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
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
            quantity_sold=Sum("sale_lines__quantity"),
            net_revenue=Sum("sale_lines__total_price"),
            # Cost of Goods Sold (COGS)
            total_cost_value=Sum(F("sale_lines__quantity") * F("sale_lines__average_cost")),
        )
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