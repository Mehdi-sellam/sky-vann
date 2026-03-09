#!/usr/bin/env python
"""Test script to create product/purchase/transfer/sale and print analytics for a user.

Run with: python skyvan/scripts/test_statistics_user_retrieve.py
Make sure your virtualenv is activated and DJANGO_SETTINGS_MODULE is set or let the script set it.
"""
import os
import sys
import django
import uuid
import json
from decimal import Decimal


def setup_django():
    # Ensure the inner project package directory is on sys.path so
    # `import skyvan.settings` will resolve correctly when running
    # this script from the repo root.
    project_skyvan_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_skyvan_dir not in sys.path:
        sys.path.insert(0, project_skyvan_dir)
    # Use the database configured in skyvan.settings (do not override DATABASE_URL).
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skyvan.settings")
    # If debug_toolbar is referenced in settings but not installed in this
    # environment, remove it from INSTALLED_APPS and MIDDLEWARE to allow
    # django.setup() to proceed for this standalone script.
    try:
        import importlib

        settings_mod = importlib.import_module("skyvan.settings")
        if hasattr(settings_mod, "INSTALLED_APPS"):
            settings_mod.INSTALLED_APPS = [
                a for a in settings_mod.INSTALLED_APPS if a != "debug_toolbar"
            ]
        if hasattr(settings_mod, "MIDDLEWARE"):
            settings_mod.MIDDLEWARE = [
                m for m in settings_mod.MIDDLEWARE if "debug_toolbar" not in m
            ]
    except Exception:
        # ignore and continue; django.setup() will raise if there's another issue
        pass

    django.setup()


def main():
    setup_django()

    from account.models import User
    from product.models import Category, Product
    from warehouse.models import Warehouse
    from supplier.models import Supplier
    from purchases.models import PurchaseOrder, PurchaseLine
    from transfer.models import Transfer, TransferLine
    from transfer.enum import TransferType, TransferStatus
    from van.models import Van, VanAssignment
    from customer.models import Customer
    from sales.models import SaleOrder, SaleLine
    from analytics.services import get_user_van_analytics_data
    from analytics.serializers import UserStatisticsSerializer

    # Clean up any existing test data so script can be run multiple times
    print("Cleaning up existing test data...")
    User.objects.filter(phone="9999990000").delete()
    Warehouse.objects.filter(location="Test Location").delete()
    Supplier.objects.filter(phone="8887770000").delete()
    Product.objects.filter(sku="TP-001").delete()
    Category.objects.filter(name="Test Cat").delete()
    Customer.objects.filter(phone="7776660000").delete()
    Van.objects.filter(license_plate="LP-TEST-001").delete()
    print("Cleanup complete. Starting test...\n")

    # Create a test user (use phone for lookup, uuid in defaults)
    test_phone = "9999990000"
    user, created = User.objects.get_or_create(
        phone=test_phone,
        defaults={
            "uuid": uuid.uuid4(),
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        },
    )

    # Create a van (use license_plate for lookup, uuid in defaults)
    van, _ = Van.objects.get_or_create(
        license_plate="LP-TEST-001",
        defaults={
            "uuid": uuid.uuid4(),
            "name": "Test Van",
            "capacity": Decimal("1000.00"),
        },
    )

    # Assign van to user
    van_assignment, _ = VanAssignment.objects.get_or_create(
        van=van,
        user=user,
        defaults={
            "uuid": uuid.uuid4(),
        },
    )

    # Create a warehouse (use location for lookup)
    warehouse, _ = Warehouse.objects.get_or_create(
        location="Test Location",
        defaults={
            "uuid": uuid.uuid4(),
            "name": "Test Warehouse",
        },
    )

    # Create a supplier (use phone for lookup, uuid in defaults)
    supplier_phone = "8887770000"
    supplier, _ = Supplier.objects.get_or_create(
        phone=supplier_phone,
        defaults={
            "uuid": uuid.uuid4(),
            "name": "Test Supplier",
            "email": "supplier@example.com",
            "address": "Supplier address",
        },
    )

    # Create a product category (use name for lookup)
    category, _ = Category.objects.get_or_create(
        name="Test Cat",
        defaults={"uuid": uuid.uuid4()},
    )

    # Create a product (use sku for lookup)
    product, _ = Product.objects.get_or_create(
        sku="TP-001",
        defaults={
            "uuid": uuid.uuid4(),
            "name": "Test Product",
            "price": Decimal("10.00"),
            "cost_price": Decimal("6.00"),
            "average_cost": Decimal("6.00"),
            "category": category,
        },
    )

    # Create a purchase order and line (receive into warehouse)
    po_uuid = uuid.uuid4()
    purchase_order = PurchaseOrder.objects.create(
        uuid=po_uuid,
        supplier=supplier,
        warehouse=warehouse,
    )
    PurchaseLine.objects.create(
        uuid=uuid.uuid4(),
        purchase_order=purchase_order,
        product=product,
        quantity=Decimal("100.00"),
        unit_price=Decimal("10.00"),
    )
    purchase_order.is_received = True
    purchase_order.save()

    # Create a transfer from warehouse to van
    tr_uuid = uuid.uuid4()
    transfer = Transfer.objects.create(
        uuid=tr_uuid,
        transfer_type=TransferType.WAREHOUSE_TO_VAN,
        source_warehouse=warehouse,
        destination_van=van,
        status=TransferStatus.ACCEPTED,
    )
    TransferLine.objects.create(
        uuid=uuid.uuid4(),
        transfer=transfer,
        product=product,
        quantity=Decimal("50.00"),
    )

    # Create a customer (use phone for lookup)
    customer, _ = Customer.objects.get_or_create(
        phone="7776660000",
        defaults={
            "uuid": uuid.uuid4(),
            "name": "Test Customer",
            "email": "cust@example.com",
            "address": "Cust address",
        },
    )

    # Make a sale from the van
    so_uuid = uuid.uuid4()
    sale_order = SaleOrder.objects.create(
        uuid=so_uuid,
        customer=customer,
        van=van,
    )
    SaleLine.objects.create(
        uuid=uuid.uuid4(),
        sale_order=sale_order,
        product=product,
        quantity=Decimal("20.00"),
        unit_price=Decimal("12.00"),
    )

    # Now fetch analytics data using the internal service and serialize
    data = get_user_van_analytics_data(user.uuid)
    serializer = UserStatisticsSerializer(data)

    print("\n✓ Test script completed successfully!")
    print("\nAnalytics response:")
    print(json.dumps(serializer.data, indent=2, default=str))


if __name__ == "__main__":
    main()
