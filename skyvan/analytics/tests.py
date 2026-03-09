from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from account.models import User
from customer.models import Customer
from product.models import Category, Product
from return_sales.models import ReturnSaleOrder, ReturnSaleLine
from sales.models import SaleOrder, SaleLine
from transfer.enum import TransferType, TransferStatus
from transfer.models import Transfer, TransferLine
from van.models import Van, VanAssignment
from warehouse.models import Warehouse


class ProductStatisticsViewTests(TestCase):
    """
    End‑to‑end tests for `/analytics/statistics/user/<uuid>/`.

    These tests intentionally exercise the main edge‑cases:
    - Opening balance before the requested window.
    - Temporal van ownership (assignment windows).
    - Status filters (accepted transfers, received sales/returns only).
    - Returns going to warehouse, not back to van stock.
    - Returns created by someone else but attributable to the driver.
    """

    def setUp(self) -> None:
        self.user = User.objects.create(
            uuid=uuid.uuid4(),
            first_name="Driver",
            last_name="One",
            phone="1000000000",
        )
        self.manager = User.objects.create(
            uuid=self._new_uuid(),
            first_name="Manager",
            last_name="One",
            phone="2000000000",
        )

        self.van_a = Van.objects.create(
            uuid=self._new_uuid(),
            name="Van A",
            license_plate="AAA-111",
            capacity=Decimal("1000.00"),
        )
        self.van_b = Van.objects.create(
            uuid=self._new_uuid(),
            name="Van B",
            license_plate="BBB-222",
            capacity=Decimal("1000.00"),
        )

        self.category = Category.objects.create(uuid=self._new_uuid(), name="Cat")
        self.product = Product.objects.create(
            uuid=self._new_uuid(),
            name="P1",
            sku="SKU-1",
            product_type="stock",
            category=self.category,
            price=Decimal("10.00"),
            cost_price=Decimal("6.00"),
            average_cost=Decimal("6.00"),
        )

        self.warehouse = Warehouse.objects.create(
            uuid=self._new_uuid(),
            name="Main WH",
            location="Main",
        )

        self.customer = Customer.objects.create(
            uuid=self._new_uuid(),
            name="Cust",
            phone="3000000000",
        )

        self.base_day = timezone.make_aware(datetime(2025, 1, 10))

    def _new_uuid(self):
        import uuid

        return uuid.uuid4()

    def _assign(self, van, user, start, end=None):
        return VanAssignment.objects.create(
            uuid=self._new_uuid(),
            van=van,
            user=user,
            start_datetime=start,
            end_datetime=end,
            is_active=end is None,
        )

    def _transfer(self, *, when, product_qty, src_van=None, dst_van=None):
        transfer = Transfer.objects.create(
            uuid=self._new_uuid(),
            transfer_type=(
                TransferType.WAREHOUSE_TO_VAN
                if dst_van
                else TransferType.VAN_TO_WAREHOUSE
            ),
            source_van=src_van,
            destination_van=dst_van,
            source_warehouse=self.warehouse if not src_van else None,
            destination_warehouse=self.warehouse if not dst_van else None,
            status=TransferStatus.ACCEPTED,
        )
        # Manually adjust timestamps because `created_at` is auto_now_add
        Transfer.objects.filter(pk=transfer.pk).update(created_at=when)
        transfer.refresh_from_db()

        line = TransferLine.objects.create(
            uuid=self._new_uuid(),
            transfer=transfer,
            product=self.product,
            quantity=product_qty,
        )
        TransferLine.objects.filter(pk=line.pk).update(created_at=when)
        return transfer

    def _sale(self, *, when, van, qty, created_by=None, is_received=True):
        order = SaleOrder.objects.create(
            uuid=self._new_uuid(),
            customer=self.customer,
            van=van,
            warehouse=None,
            is_received=is_received,
            created_by=created_by or self.user,
        )
        SaleOrder.objects.filter(pk=order.pk).update(created_at=when)
        order.refresh_from_db()

        line = SaleLine.objects.create(
            uuid=self._new_uuid(),
            sale_order=order,
            product=self.product,
            quantity=qty,
            unit_price=Decimal("10.00"),
        )
        SaleLine.objects.filter(pk=line.pk).update(created_at=when)
        return order

    def _return(self, *, when, qty, created_by):
        order = ReturnSaleOrder.objects.create(
            uuid=self._new_uuid(),
            customer=self.customer,
            warehouse=self.warehouse,
            is_received=True,
            created_by=created_by,
        )
        ReturnSaleOrder.objects.filter(pk=order.pk).update(created_at=when)
        order.refresh_from_db()

        line = ReturnSaleLine.objects.create(
            uuid=self._new_uuid(),
            return_sale_order=order,
            product=self.product,
            quantity=qty,
            unit_price=Decimal("10.00"),
        )
        ReturnSaleLine.objects.filter(pk=line.pk).update(created_at=when)
        return order

    def _call_endpoint(self, start, end):
        url = reverse(
            "product-statistics",
            kwargs={"uuid": str(self.user.uuid)},
        )
        resp = self.client.get(
            url,
            {
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(resp.status_code, 200, msg=resp.json())
        data = resp.json()
        self.assertIn("results", data, msg=data)
        # Fail with full payload if no results returned, for easier debugging
        self.assertGreater(len(data["results"]), 0, msg=data)
        return data["results"]

    def test_opening_balance_and_period_movements(self):
        """
        Stock before the window counts as opening balance,
        and remaining_quantity is opening + in - out - sales.
        """
        assign_start = self.base_day - timedelta(days=5)
        self._assign(self.van_a, self.user, assign_start)

        # Before window: +100 in, -30 out, -10 sold => opening = 60
        before = self.base_day - timedelta(days=2)
        self._transfer(when=before, product_qty=Decimal("100.00"), dst_van=self.van_a)
        self._transfer(when=before, product_qty=Decimal("30.00"), src_van=self.van_a)
        self._sale(when=before, van=self.van_a, qty=Decimal("10.00"))

        # In window: +40 in, -20 out, -5 sold => net +15 during window
        start = self.base_day
        end = self.base_day + timedelta(days=2)
        in_window = self.base_day + timedelta(hours=1)
        self._transfer(when=in_window, product_qty=Decimal("40.00"), dst_van=self.van_a)
        self._transfer(when=in_window, product_qty=Decimal("20.00"), src_van=self.van_a)
        self._sale(when=in_window, van=self.van_a, qty=Decimal("5.00"))

        results = self._call_endpoint(start, end)
        row = results[0]

        self.assertEqual(Decimal(row["quantity_transfered_warehouse_to_van"]), Decimal("40.00"))
        self.assertEqual(Decimal(row["quantity_transfered_van_to_warehouse"]), Decimal("20.00"))
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("5.00"))
        # remaining = 60 opening + 40 - 20 - 5 = 75
        self.assertEqual(Decimal(row["remaining_quantity"]), Decimal("75.00"))

    def test_temporal_van_ownership_excludes_old_van(self):
        """
        Movements on vans outside the assignment window must be ignored.
        """
        # User had van A in 2025, then van B in 2026.
        assign_a = self.base_day - timedelta(days=365)
        self._assign(self.van_a, self.user, assign_a, end=assign_a + timedelta(days=100))

        assign_b = self.base_day
        self._assign(self.van_b, self.user, assign_b)

        # Transfer & sale on van A long before window -> should not appear.
        old = assign_a + timedelta(days=10)
        self._transfer(when=old, product_qty=Decimal("50.00"), dst_van=self.van_a)
        self._sale(when=old, van=self.van_a, qty=Decimal("5.00"))

        # Transfer & sale on van B within window -> should appear.
        start = self.base_day
        end = self.base_day + timedelta(days=2)
        now = self.base_day + timedelta(hours=1)
        self._transfer(when=now, product_qty=Decimal("30.00"), dst_van=self.van_b)
        self._sale(when=now, van=self.van_b, qty=Decimal("3.00"))

        results = self._call_endpoint(start, end)
        row = results[0]
        self.assertEqual(Decimal(row["quantity_transfered_warehouse_to_van"]), Decimal("30.00"))
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("3.00"))

    def test_pending_and_unreceived_sales_are_ignored(self):
        """
        Only is_received=True sales contribute to statistics.
        """
        assign_start = self.base_day - timedelta(days=1)
        self._assign(self.van_a, self.user, assign_start)

        start = self.base_day
        end = self.base_day + timedelta(days=1)
        when = self.base_day + timedelta(hours=1)

        # Unreceived sale should not be counted
        self._sale(when=when, van=self.van_a, qty=Decimal("10.00"), is_received=False)

        # Received sale is counted
        self._sale(when=when, van=self.van_a, qty=Decimal("5.00"), is_received=True)

        results = self._call_endpoint(start, end)
        row = results[0]
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("5.00"))

    def test_return_goes_to_warehouse_not_back_to_van_stock(self):
        """
        Returns should not increase remaining_quantity on the van.
        """
        assign_start = self.base_day - timedelta(days=1)
        self._assign(self.van_a, self.user, assign_start)

        # Opening: 50 in, no out, no sales -> opening = 50
        before = self.base_day - timedelta(hours=1)
        self._transfer(when=before, product_qty=Decimal("50.00"), dst_van=self.van_a)

        # In window: sell 10, then customer returns 4 (to warehouse)
        start = self.base_day
        end = self.base_day + timedelta(days=1)
        when_sale = self.base_day + timedelta(hours=1)
        self._sale(when=when_sale, van=self.van_a, qty=Decimal("10.00"))

        when_ret = self.base_day + timedelta(hours=2)
        self._return(when=when_ret, qty=Decimal("4.00"), created_by=self.manager)

        results = self._call_endpoint(start, end)
        row = results[0]

        # Return should be reported but not added back into remaining_quantity
        self.assertEqual(Decimal(row["quantity_returned_sale"]), Decimal("4.00"))
        # remaining = 50 opening + 0 in - 0 out - 10 sold = 40
        self.assertEqual(Decimal(row["remaining_quantity"]), Decimal("40.00"))

    def test_return_attributed_even_if_created_by_manager(self):
        """
        Returns are attributed to the driver via matching prior sales,
        not by created_by.
        """
        assign_start = self.base_day - timedelta(days=1)
        self._assign(self.van_a, self.user, assign_start)

        # Prior sale from driver's van
        when_sale = self.base_day - timedelta(hours=1)
        self._transfer(when=when_sale, product_qty=Decimal("20.00"), dst_van=self.van_a)
        self._sale(when=when_sale, van=self.van_a, qty=Decimal("10.00"))

        # Window with manager‑created return
        start = self.base_day
        end = self.base_day + timedelta(days=1)
        when_ret = self.base_day + timedelta(hours=1)
        self._return(when=when_ret, qty=Decimal("3.00"), created_by=self.manager)

        results = self._call_endpoint(start, end)
        row = results[0]
        # Return should still be counted for this driver
        self.assertEqual(Decimal(row["quantity_returned_sale"]), Decimal("3.00"))


