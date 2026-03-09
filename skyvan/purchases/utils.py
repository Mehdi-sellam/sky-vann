from decimal import Decimal, ROUND_HALF_UP
from .models import Product, PurchaseLine
from warehouse.inventory import get_central_inventory_for_product
from django.db.models import Sum, F
from sales.models import SaleLine


def recalculate_average_cost(product):
    """Recalculates and returns the weighted average cost after a purchase or sale update."""

    # Get the central inventory for this product
    central_inventory = get_central_inventory_for_product(product)

    # Get total purchased quantity (excluding soft-deleted purchases)
    total_purchased_quantity = PurchaseLine.objects.filter(
        deleted=False, product=product
    ).aggregate(total=Sum("quantity"))["total"] or Decimal(0)

    # Get total sold quantity (excluding soft-deleted sales)
    total_sold_quantity = SaleLine.objects.filter(
        sale_order__deleted=False, product=product
    ).aggregate(total=Sum("quantity"))["total"] or Decimal(0)

    # Calculate remaining stock in inventory
    total_quantity = (
        central_inventory.physical_quantity if central_inventory else Decimal(0)
    )

    # Ensure total stock is correct: Purchased - Sold
    total_quantity = total_purchased_quantity - total_sold_quantity

    # Get total cost from purchases
    total_cost = PurchaseLine.objects.filter(deleted=False, product=product).aggregate(
        total=Sum(F("quantity") * F("unit_price"))
    )["total"] or Decimal(0)

    # Calculate new average cost
    if total_quantity > 0:
        average_cost = total_cost / total_quantity
    else:
        average_cost = product.average_cost or Decimal(0)

    return average_cost


def calculate_average_cost(
    product: Product,
    quantity: Decimal,
    unit_price: Decimal,
) -> Decimal:

    # Get the central inventory record
    central_inventory = get_central_inventory_for_product(product)

    # Ensure values are valid Decimals
    current_average_cost = Decimal(product.average_cost or 0)
    current_quantity = Decimal(central_inventory.physical_quantity or 0)

    # Get current total cost
    total_cost = current_average_cost * current_quantity

    # Calculate the cost of the new purchase
    added_cost = Decimal(quantity) * unit_price

    # Calculate the new total cost and quantity
    new_total_cost = total_cost + added_cost
    new_total_quantity = current_quantity + quantity

    # Calculate new weighted average cost
    if new_total_quantity > 0:
        average_cost = new_total_cost / new_total_quantity
        average_cost = (new_total_cost / new_total_quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        average_cost = product.average_cost or Decimal(0)

    return average_cost
