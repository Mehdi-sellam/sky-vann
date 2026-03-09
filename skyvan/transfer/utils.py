from django.db import transaction
from product.models import Product
from .models import Transfer, TransferLine
from warehouse.inventory import increase_central_inventory, decrease_central_inventory
from .error_codes import TransferErrorCode
from .enum import TransferType
from warehouse.models import Inventory, Warehouse
from van.models import VanInventory, Van
from rest_framework.exceptions import ValidationError, NotFound
from .error_codes import TransferErrorCode
from decimal import Decimal


@transaction.atomic
def decrease_van_inventory_quantity(product: Product, quantity, van: Van):
    """
    Decreases the inventory quantity of a product in a van by the given quantity.
    Raises NotFound if inventory doesn't exist, or ValidationError if stock is insufficient.
    """
    try:
        with transaction.atomic():
            inventory = VanInventory.objects.select_for_update().get(
                product=product, van=van
            )
    except VanInventory.DoesNotExist:
        raise NotFound(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"Inventory for product '{product.name}' not found in van '{van.name}'.",
                "field": "inventory",
            }
        )

    if inventory.quantity < quantity:
        raise ValidationError(
            {
                "code": TransferErrorCode.INSUFFICIENT_STOCK.value,
                "message": f"Not enough stock in van '{van.name}' for product '{product.name}'. "
                f"Required: {quantity}, Available: {inventory.quantity}",
                "field": "quantity",
            }
        )

    inventory.quantity -= quantity
    inventory.save()


def increase_van_inventory_quantity(product: Product, quantity, van: Van):
    """
    Increases the inventory quantity of a product in a van by the given quantity.
    If the inventory doesn't exist, it creates it.
    """
    try:
        with transaction.atomic():
            inventory, _ = VanInventory.objects.select_for_update().get_or_create(
                product=product, van=van
            )
            inventory.quantity += quantity
            inventory.save()
    except VanInventory.DoesNotExist:
        raise NotFound(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"Inventory for product '{product.name}' not found in van '{van.name}'.",
                "field": "inventory",
            }
        )
    except Exception as e:
        raise ValidationError(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"Error increasing stock in van '{van.name}' for product '{product.name}': {str(e)}",
                "field": "increase_inventory_quantity",
            }
        )


@transaction.atomic
def decrease_inventory_quantity(product: Product, quantity, warehouse: Warehouse):
    """
    Safely decreases the inventory quantity of a product in a warehouse.
    Rolls back if stock is insufficient or an error occurs.
    """
    try:
        # Lock the inventory row to avoid race conditions
        inventory = Inventory.objects.select_for_update().get(
            product=product, warehouse=warehouse
        )
    except Inventory.DoesNotExist:
        raise ValidationError(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"No inventory record found for product '{product}' in the selected warehouse.",
                "field": "inventory",
            }
        )

    if inventory.logical_quantity < quantity or inventory.physical_quantity < quantity:
        raise ValidationError(
            {
                "code": TransferErrorCode.INSUFFICIENT_STOCK.value,
                "message": (
                    f"Insufficient stock for product '{product.name}' in warehouse '{warehouse.name}'. "
                    f"Required: {quantity}, Available: {inventory.logical_quantity}"
                ),
                "field": "quantity",
            }
        )

    # Perform the stock reduction
    inventory.logical_quantity -= quantity
    inventory.physical_quantity -= quantity
    inventory.save()


@transaction.atomic
def increase_inventory_quantity(product: Product, quantity, warehouse: Warehouse):
    """
    Safely increases the inventory quantity of a product in a warehouse.
    Creates the inventory record if it doesn't exist.
    """
    try:
        inventory, _ = Inventory.objects.select_for_update().get_or_create(
            product=product, warehouse=warehouse
        )
        inventory.logical_quantity += quantity
        inventory.physical_quantity += quantity
        inventory.save()

    except Exception as e:
        raise ValidationError(
            {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": f"Failed to increase inventory: {str(e)}",
                "field": "increase_inventory_quantity",
            }
        )


# ------------------- fix quantities ------------------
def adjust_quantities_van_to_warehouse(
    product: Product, quantity, source_van: Van, destination_warehouse: Warehouse
):
    """
    Fixes the logical and physical quantities of all the inventories.
    """
    decrease_van_inventory_quantity(product=product, quantity=quantity, van=source_van)
    increase_inventory_quantity(
        product=product, quantity=quantity, warehouse=destination_warehouse
    )


def adjust_quantities_warehouse_to_van(
    product: Product, quantity, source_warehouse: Warehouse, destination_van: Van
):
    """
    Fixes the logical and physical quantities of all the inventories.
    """
    decrease_inventory_quantity(
        product=product, quantity=quantity, warehouse=source_warehouse
    )
    increase_van_inventory_quantity(
        product=product, quantity=quantity, van=destination_van
    )


def adjust_quantities_warehouse_to_warehouse(
    product: Product,
    quantity,
    source_warehouse: Warehouse,
    destination_warehouse: Warehouse,
):
    """
    Fixes the logical and physical quantities of all the inventories.
    """
    decrease_inventory_quantity(
        product=product, quantity=quantity, warehouse=source_warehouse
    )
    increase_inventory_quantity(
        product=product, quantity=quantity, warehouse=destination_warehouse
    )


def adjust_quantities_van_to_van(
    product: Product, quantity, source_van: Van, destination_van: Van
):
    """
    Fixes the logical and physical quantities of all the inventories.
    """
    decrease_van_inventory_quantity(product=product, quantity=quantity, van=source_van)
    increase_van_inventory_quantity(
        product=product, quantity=quantity, van=destination_van
    )


def delete_transfer_line(
    transfer_type,
    line,
    source_van=None,
    destination_van=None,
    source_warehouse=None,
    destination_warehouse=None,
):

    product = line.product
    quantity = line.quantity

    if transfer_type == TransferType.VAN_TO_WAREHOUSE:
        adjust_quantities_van_to_warehouse(
            product=product,
            quantity=quantity,
            source_warehouse=source_warehouse,
            destination_van=destination_van,
        )
    elif transfer_type == TransferType.WAREHOUSE_TO_VAN:
        adjust_quantities_van_to_warehouse(
            product=product,
            quantity=quantity,
            source_van=source_van,
            destination_warehouse=destination_warehouse,
        )
    elif transfer_type == TransferType.WAREHOUSE_TO_WAREHOUSE:
        adjust_quantities_warehouse_to_warehouse(
            product=product,
            quantity=quantity,
            source_warehouse=destination_warehouse,
            destination_warehouse=source_warehouse,
        )
    elif transfer_type == TransferType.VAN_TO_VAN:
        adjust_quantities_van_to_van(
            product=product,
            quantity=quantity,
            source_van=destination_van,
            destination_van=source_van,
        )
    else:
        raise ValidationError(
            {
                "code": TransferErrorCode.INVALID_TRANSFER_TYPE,
                "message": f"Invalid transfer type: {transfer_type}",
                "field": "transfer_type",
            }
        )

    line.deleted = True
    line.save()
