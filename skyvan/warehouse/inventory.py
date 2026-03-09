from django.db import transaction
from .models import Inventory, Warehouse, CentralInventory, Product
from django.conf import settings
import uuid
from decimal import Decimal


def create_default_warehouse(warehouse_name=settings.DEFAULT_WAREHOUSE_NAME):
    """
    Creates a default warehouse with a UUID if it doesn't exist.
    """
    # wareouses =Warehouse.objects.filter(name=warehouse_.name)
    # for wareouse in wareouses:
    #     print(wareouse)
    try:
        # Check if a warehouse with the given name exists
        warehouse = Warehouse.objects.get(name=warehouse_name)
    except Warehouse.DoesNotExist:

        warehouse = Warehouse.objects.create(
            uuid=uuid.uuid4(), name=settings.DEFAULT_WAREHOUSE_NAME
        )
    return warehouse


def decrease_inventory_quantity(
    product: Product, quantity: Decimal, warehouse: Warehouse
):
    """
    Decreases the inventory quantity of a product in a warehouse by the given quantity.
    If the inventory doesn't exist, it creates it.
    """
    with transaction.atomic():

        inventory, _ = Inventory.objects.get_or_create(
            product=product, warehouse=warehouse
        )

        # Update the logical and physical quantities
        inventory.logical_quantity -= quantity
        inventory.physical_quantity -= quantity
        inventory.save()

        decrease_central_inventory(product, quantity)


def increase_inventory_quantity(product: Product, quantity, warehouse: Warehouse):
    """
    Increases the inventory quantity of a product in a warehouse by the given quantity.
    If the inventory doesn't exist, it creates it.
    """
    with transaction.atomic():

        inventory, _ = Inventory.objects.get_or_create(
            product=product, warehouse=warehouse
        )

        #     # Update the logical and physical quantities
        inventory.logical_quantity += quantity
        inventory.physical_quantity += quantity
        inventory.save()
        increase_central_inventory(product, quantity)


def increase_central_inventory(product, quantity):
    # Get the current central inventory entry or create a new one if it doesn't exist
    central_inventory, _ = CentralInventory.objects.get_or_create(product=product)

    # Update the logical and physical quantities
    central_inventory.logical_quantity += quantity
    central_inventory.physical_quantity += quantity

    # Save the changes
    central_inventory.save()


def decrease_central_inventory(product, quantity):
    # Get the current central inventory entry or create a new one if it doesn't exist
    central_inventory, created = CentralInventory.objects.get_or_create(product=product)

    # Update the logical and physical quantities
    central_inventory.logical_quantity -= quantity
    central_inventory.physical_quantity -= quantity

    # Save the changes
    central_inventory.save()


def get_central_inventory_for_product(product: Product):
    central_inventory, _ = CentralInventory.objects.get_or_create(product=product)

    return central_inventory
