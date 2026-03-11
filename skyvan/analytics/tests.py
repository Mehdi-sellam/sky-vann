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


def _new_uuid():
    return uuid.uuid4()


class ProductStatisticsViewTests(TestCase):
    """
    End-to-end tests for GET /statistics/user/<uuid>/
    Tests temporal van ownership, opening balance, status filters, and return handling.
    """

    def setUp(self):
        self.user = User.objects.create(
            uuid=_new_uuid(), first_name="Driver", last_name="One", phone="1000000000",
        )
        self.manager = User.objects.create(
            uuid=_new_uuid(), first_name="Manager", last_name="One", phone="2000000000",
        )
        self.van_a = Van.objects.create(
            uuid=_new_uuid(), name="Van A", license_plate="AAA-111", capacity=Decimal("1000.00"),
        )
        self.van_b = Van.objects.create(
            uuid=_new_uuid(), name="Van B", license_plate="BBB-222", capacity=Decimal("1000.00"),
        )
        self.category = Category.objects.create(uuid=_new_uuid(), name="Cat")
        self.product = Product.objects.create(
            uuid=_new_uuid(), name="P1", sku="SKU-1", product_type="stock",
            category=self.category, price=Decimal("10.00"),
            cost_price=Decimal("6.00"), average_cost=Decimal("6.00"),
        )
        self.warehouse = Warehouse.objects.create(uuid=_new_uuid(), name="Main WH", location="Main")
        self.customer = Customer.objects.create(uuid=_new_uuid(), name="Cust", phone="3000000000")
        self.base_day = timezone.make_aware(datetime(2025, 1, 10))

    def _assign(self, van, user, start, end=None):
        return VanAssignment.objects.create(
            uuid=_new_uuid(), van=van, user=user,
            start_datetime=start,
            end_datetime=end or (start + timedelta(days=365)),
            is_active=end is None,
        )

    def _transfer(self, *, when, product_qty, src_van=None, dst_van=None, created_by=None):
        transfer = Transfer.objects.create(
            uuid=_new_uuid(),
            transfer_type=TransferType.WAREHOUSE_TO_VAN if dst_van else TransferType.VAN_TO_WAREHOUSE,
            source_van=src_van,
            destination_van=dst_van,
            source_warehouse=self.warehouse if not src_van else None,
            destination_warehouse=self.warehouse if not dst_van else None,
            status=TransferStatus.ACCEPTED,
            created_by=created_by or self.user,
        )
        Transfer.objects.filter(pk=transfer.pk).update(created_at=when, updated_at=when)
        transfer.refresh_from_db()
        line = TransferLine.objects.create(
            uuid=_new_uuid(), transfer=transfer, product=self.product, quantity=product_qty,
        )
        TransferLine.objects.filter(pk=line.pk).update(created_at=when)
        return transfer

    def _sale(self, *, when, van, qty, created_by=None, is_received=True):
        order = SaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, van=van, warehouse=None,
            is_received=is_received, created_by=created_by or self.user,
        )
        SaleOrder.objects.filter(pk=order.pk).update(created_at=when)
        order.refresh_from_db()
        line = SaleLine.objects.create(
            uuid=_new_uuid(), sale_order=order, product=self.product,
            quantity=qty, unit_price=Decimal("10.00"),
        )
        SaleLine.objects.filter(pk=line.pk).update(created_at=when)
        return order

    def _return(self, *, when, qty, created_by):
        order = ReturnSaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, warehouse=self.warehouse,
            is_received=True, created_by=created_by,
        )
        ReturnSaleOrder.objects.filter(pk=order.pk).update(created_at=when)
        order.refresh_from_db()
        line = ReturnSaleLine.objects.create(
            uuid=_new_uuid(), return_sale_order=order, product=self.product,
            quantity=qty, unit_price=Decimal("10.00"),
        )
        ReturnSaleLine.objects.filter(pk=line.pk).update(created_at=when)
        return order

    def _call_endpoint(self, start, end, van_uuids=None):
        url = reverse("product-statistics", kwargs={"uuid": str(self.user.uuid)})
        resp = self.client.get(url, {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "van_uuids": van_uuids or str(self.van_a.uuid),
        })
        self.assertEqual(resp.status_code, 200, msg=resp.json())
        data = resp.json()
        self.assertIn("results", data)
        self.assertGreater(len(data["results"]), 0, msg=data)
        return data["results"]

    def test_opening_balance_and_period_movements(self):
        """Opening stock before window, movements in window, remaining = opening + in - out - sold."""
        assign_start = self.base_day - timedelta(days=5)
        self._assign(self.van_a, self.user, assign_start)

        before = self.base_day - timedelta(days=2)
        self._transfer(when=before, product_qty=Decimal("100.00"), dst_van=self.van_a)
        self._transfer(when=before, product_qty=Decimal("30.00"), src_van=self.van_a)
        self._sale(when=before, van=self.van_a, qty=Decimal("10.00"))

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
        self.assertEqual(Decimal(row["remaining_quantity"]), Decimal("75.00"))

    def test_temporal_van_ownership_excludes_movements_outside_assignment(self):
        """Movements on vans not owned in the requested period must be excluded."""
        old_end = self.base_day - timedelta(days=200)
        self._assign(self.van_a, self.user, self.base_day - timedelta(days=365), end=old_end)
        self._assign(self.van_b, self.user, self.base_day)

        old = self.base_day - timedelta(days=300)
        self._transfer(when=old, product_qty=Decimal("50.00"), dst_van=self.van_a)
        self._sale(when=old, van=self.van_a, qty=Decimal("5.00"))

        start = self.base_day
        end = self.base_day + timedelta(days=2)
        now = self.base_day + timedelta(hours=1)
        self._transfer(when=now, product_qty=Decimal("30.00"), dst_van=self.van_b)
        self._sale(when=now, van=self.van_b, qty=Decimal("3.00"))

        results = self._call_endpoint(start, end, van_uuids=str(self.van_b.uuid))
        row = results[0]
        self.assertEqual(Decimal(row["quantity_transfered_warehouse_to_van"]), Decimal("30.00"))
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("3.00"))

    def test_unreceived_sales_excluded(self):
        """Only is_received=True sales contribute to statistics."""
        self._assign(self.van_a, self.user, self.base_day - timedelta(days=1))
        start = self.base_day
        end = self.base_day + timedelta(days=1)
        when = self.base_day + timedelta(hours=1)
        self._sale(when=when, van=self.van_a, qty=Decimal("10.00"), is_received=False)
        self._sale(when=when, van=self.van_a, qty=Decimal("5.00"), is_received=True)

        results = self._call_endpoint(start, end)
        row = results[0]
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("5.00"))

    def test_return_not_added_back_to_van_remaining(self):
        """Returns go to warehouse, not back to van stock - remaining = opening + in - sold."""
        self._assign(self.van_a, self.user, self.base_day - timedelta(days=1))
        before = self.base_day - timedelta(hours=1)
        self._transfer(when=before, product_qty=Decimal("50.00"), dst_van=self.van_a)

        start = self.base_day
        end = self.base_day + timedelta(days=1)
        self._sale(when=self.base_day + timedelta(hours=1), van=self.van_a, qty=Decimal("10.00"))
        self._return(when=self.base_day + timedelta(hours=2), qty=Decimal("4.00"), created_by=self.manager)

        results = self._call_endpoint(start, end)
        row = results[0]
        self.assertEqual(Decimal(row["quantity_returned_sale"]), Decimal("0.00"))
        self.assertEqual(Decimal(row["remaining_quantity"]), Decimal("40.00"))

    def test_return_quantity_returned_sale_is_zero_when_not_tracked_on_van(self):
        """quantity_returned_sale is currently zero (returns go to warehouse)."""
        self._assign(self.van_a, self.user, self.base_day - timedelta(days=1))
        before = self.base_day - timedelta(hours=1)
        self._transfer(when=before, product_qty=Decimal("20.00"), dst_van=self.van_a)
        self._sale(when=before, van=self.van_a, qty=Decimal("10.00"))

        start = self.base_day
        end = self.base_day + timedelta(days=1)
        self._return(when=self.base_day + timedelta(hours=1), qty=Decimal("3.00"), created_by=self.manager)

        results = self._call_endpoint(start, end)
        row = results[0]
        self.assertEqual(Decimal(row["quantity_returned_sale"]), Decimal("0.00"))

    def test_missing_van_uuid_returns_400(self):
        url = reverse("product-statistics", kwargs={"uuid": str(self.user.uuid)})
        resp = self.client.get(url, {
            "start_date": "2025-01-10", "end_date": "2025-01-12",
        })
        self.assertEqual(resp.status_code, 400)

    def test_missing_date_params_returns_400(self):
        url = reverse("product-statistics", kwargs={"uuid": str(self.user.uuid)})
        resp = self.client.get(url, {"van_uuids": str(self.van_a.uuid)})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_van_uuid_returns_403(self):
        self._assign(self.van_a, self.user, self.base_day - timedelta(days=1))
        url = reverse("product-statistics", kwargs={"uuid": str(self.user.uuid)})
        resp = self.client.get(url, {
            "start_date": "2025-01-10", "end_date": "2025-01-12",
            "van_uuids": str(_new_uuid()),
        })
        self.assertEqual(resp.status_code, 403)


class MostSoldProductsTests(TestCase):
    """
    Unit tests for GET /statistics/most-sold-products/

    Endpoint returns top 10 products by net quantity sold (sales - returns).
    Uses SQL LIMIT 10 which avoids fetching all rows - more efficient than
    client-side slicing when there are many products.
    """

    def setUp(self):
        self.url = reverse("most-sold-products")
        self.category = Category.objects.create(uuid=_new_uuid(), name="Cat")
        self.user = User.objects.create(uuid=_new_uuid(), phone="5000000001")
        self.warehouse = Warehouse.objects.create(uuid=_new_uuid(), name="WH", location="L")
        self.customer = Customer.objects.create(uuid=_new_uuid(), name="C", phone="5000000002")

    def _product(self, name, sku, avg_cost="5.00"):
        return Product.objects.create(
            uuid=_new_uuid(), name=name, sku=sku, product_type="stock",
            category=self.category, price=Decimal("10.00"),
            cost_price=Decimal("5.00"), average_cost=Decimal(avg_cost),
        )

    def _sale(self, product, qty, unit_price="10.00", is_received=True):
        order = SaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, van=None,
            warehouse=self.warehouse, is_received=is_received, created_by=self.user,
        )
        SaleLine.objects.create(
            uuid=_new_uuid(), sale_order=order, product=product,
            quantity=Decimal(str(qty)), unit_price=Decimal(unit_price),
            average_cost=Decimal("5.00"),
        )
        return order

    def _return(self, product, qty, unit_price="10.00", is_received=True):
        order = ReturnSaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, warehouse=self.warehouse,
            is_received=is_received, created_by=self.user,
        )
        ReturnSaleLine.objects.create(
            uuid=_new_uuid(), return_sale_order=order, product=product,
            quantity=Decimal(str(qty)), unit_price=Decimal(unit_price),
            average_cost=Decimal("5.00"),
        )
        return order

    def test_empty_database_returns_empty_list(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_single_product_single_sale(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product"]["name"], "Widget")
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("5"))

    def test_multiple_sales_are_summed(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 3)
        self._sale(p, 7)
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("10"))

    def test_returns_reduce_quantity_sold(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 10)
        self._return(p, 3)
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("7"))

    def test_fully_returned_product_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        self._return(p, 5)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_net_negative_quantity_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 3)
        self._return(p, 6)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_unreceived_sales_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 10, is_received=False)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_unreceived_returns_not_subtracted(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 10)
        self._return(p, 5, is_received=False)
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("10"))

    def test_deleted_product_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 10)
        p.deleted = True
        p.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_deleted_sale_order_excluded(self):
        p = self._product("Widget", "W-1")
        order = self._sale(p, 10)
        order.deleted = True
        order.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_deleted_sale_line_excluded(self):
        p = self._product("Widget", "W-1")
        order = self._sale(p, 10)
        line = order.lines.first()
        line.deleted = True
        line.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_sorted_by_quantity_sold_descending(self):
        p1 = self._product("Alpha", "A-1")
        p2 = self._product("Beta", "B-1")
        p3 = self._product("Gamma", "G-1")
        self._sale(p1, 5)
        self._sale(p2, 20)
        self._sale(p3, 10)
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["Beta", "Gamma", "Alpha"])

    def test_tie_broken_by_name_ascending(self):
        p1 = self._product("Zebra", "Z-1")
        p2 = self._product("Apple", "AP-1")
        self._sale(p1, 5)
        self._sale(p2, 5)
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["Apple", "Zebra"])

    def test_top_10_limit_enforced(self):
        for i in range(15):
            p = self._product(f"Product{i:02d}", f"SKU-{i:02d}")
            self._sale(p, i + 1)
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 10)

    def test_top_10_contains_highest_quantity_sellers(self):
        products = []
        for i in range(15):
            p = self._product(f"Product{i:02d}", f"SKU-{i:02d}")
            self._sale(p, i + 1)
            products.append((p, i + 1))
        data = self.client.get(self.url).json()
        returned_names = {d["product"]["name"] for d in data}
        top_10 = {p.name for p, _ in sorted(products, key=lambda x: -x[1])[:10]}
        self.assertEqual(returned_names, top_10)

    def test_response_structure_has_required_fields(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        row = self.client.get(self.url).json()[0]
        self.assertIn("product", row)
        self.assertIn("quantity_sold", row)
        self.assertIn("name", row["product"])
        self.assertIn("sku", row["product"])
        self.assertIn("uuid", row["product"])
        self.assertIn("category", row["product"])


class ProductsNetRevenueTests(TestCase):
    """
    Unit tests for GET /statistics/products-net-revenue/

    Endpoint returns top 10 products by net revenue (total sale price).
    Uses SQL LIMIT 10 - avoids scanning the entire dataset on large catalogues.
    """

    def setUp(self):
        self.url = reverse("products-net-revenue")
        self.category = Category.objects.create(uuid=_new_uuid(), name="Cat")
        self.user = User.objects.create(uuid=_new_uuid(), phone="6000000001")
        self.warehouse = Warehouse.objects.create(uuid=_new_uuid(), name="WH", location="L")
        self.customer = Customer.objects.create(uuid=_new_uuid(), name="C", phone="6000000002")

    def _product(self, name, sku):
        return Product.objects.create(
            uuid=_new_uuid(), name=name, sku=sku, product_type="stock",
            category=self.category, price=Decimal("10.00"),
            cost_price=Decimal("5.00"), average_cost=Decimal("5.00"),
        )

    def _sale(self, product, qty, unit_price="10.00", is_received=True):
        order = SaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, van=None,
            warehouse=self.warehouse, is_received=is_received, created_by=self.user,
        )
        SaleLine.objects.create(
            uuid=_new_uuid(), sale_order=order, product=product,
            quantity=Decimal(str(qty)), unit_price=Decimal(unit_price),
            average_cost=Decimal("5.00"),
        )
        return order

    def test_empty_database_returns_empty_list(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_single_product_revenue_calculated(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 4, unit_price="10.00")
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 1)
        self.assertEqual(Decimal(data[0]["net_revenue"]), Decimal("40.00"))
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("4"))
        self.assertEqual(Decimal(data[0]["avg_unit_price"]), Decimal("10.00"))

    def test_multiple_sales_summed(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 2, unit_price="10.00")
        self._sale(p, 3, unit_price="10.00")
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["net_revenue"]), Decimal("50.00"))
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("5"))

    def test_deleted_sale_order_excluded(self):
        p = self._product("Widget", "W-1")
        order = self._sale(p, 5)
        order.deleted = True
        order.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_deleted_sale_line_excluded(self):
        p = self._product("Widget", "W-1")
        order = self._sale(p, 5)
        line = order.lines.first()
        line.deleted = True
        line.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_deleted_product_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        p.deleted = True
        p.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_sorted_by_net_revenue_descending(self):
        p1 = self._product("Cheap", "C-1")
        p2 = self._product("Expensive", "E-1")
        p3 = self._product("Mid", "M-1")
        self._sale(p1, 5, unit_price="2.00")
        self._sale(p2, 2, unit_price="100.00")
        self._sale(p3, 10, unit_price="5.00")
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["Expensive", "Mid", "Cheap"])

    def test_tie_broken_by_name_ascending(self):
        p1 = self._product("Zebra", "Z-1")
        p2 = self._product("Apple", "AP-1")
        self._sale(p1, 10, unit_price="5.00")
        self._sale(p2, 10, unit_price="5.00")
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["Apple", "Zebra"])

    def test_top_10_limit_enforced(self):
        for i in range(15):
            p = self._product(f"Product{i:02d}", f"SKU-{i:02d}")
            self._sale(p, i + 1, unit_price=str((i + 1) * 10))
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 10)

    def test_avg_unit_price_is_weighted_average(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 2, unit_price="10.00")
        self._sale(p, 8, unit_price="5.00")
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("10"))
        expected_rev = Decimal("20.00") + Decimal("40.00")
        self.assertEqual(Decimal(data[0]["net_revenue"]), expected_rev)
        self.assertEqual(Decimal(data[0]["avg_unit_price"]), expected_rev / Decimal("10"))

    def test_response_structure_has_required_fields(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        row = self.client.get(self.url).json()[0]
        self.assertIn("product", row)
        self.assertIn("quantity_sold", row)
        self.assertIn("net_revenue", row)
        self.assertIn("avg_unit_price", row)


class ProductsProfitTests(TestCase):
    """
    Unit tests for GET /statistics/products-profit/

    Endpoint returns top 10 products by profit (net revenue - COGS), accounting for returns.
    COGS uses the snapshot average_cost field on each SaleLine/ReturnSaleLine.
    Uses SQL LIMIT 10 for performance.
    """

    def setUp(self):
        self.url = reverse("products-profit")
        self.category = Category.objects.create(uuid=_new_uuid(), name="Cat")
        self.user = User.objects.create(uuid=_new_uuid(), phone="7000000001")
        self.warehouse = Warehouse.objects.create(uuid=_new_uuid(), name="WH", location="L")
        self.customer = Customer.objects.create(uuid=_new_uuid(), name="C", phone="7000000002")

    def _product(self, name, sku, avg_cost="5.00"):
        return Product.objects.create(
            uuid=_new_uuid(), name=name, sku=sku, product_type="stock",
            category=self.category, price=Decimal("10.00"),
            cost_price=Decimal(avg_cost), average_cost=Decimal(avg_cost),
        )

    def _sale(self, product, qty, unit_price="10.00", average_cost="5.00", is_received=True):
        order = SaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, van=None,
            warehouse=self.warehouse, is_received=is_received, created_by=self.user,
        )
        SaleLine.objects.create(
            uuid=_new_uuid(), sale_order=order, product=product,
            quantity=Decimal(str(qty)), unit_price=Decimal(unit_price),
            average_cost=Decimal(average_cost),
        )
        return order

    def _return(self, product, qty, unit_price="10.00", average_cost="5.00", is_received=True):
        order = ReturnSaleOrder.objects.create(
            uuid=_new_uuid(), customer=self.customer, warehouse=self.warehouse,
            is_received=is_received, created_by=self.user,
        )
        ReturnSaleLine.objects.create(
            uuid=_new_uuid(), return_sale_order=order, product=product,
            quantity=Decimal(str(qty)), unit_price=Decimal(unit_price),
            average_cost=Decimal(average_cost),
        )
        return order

    def test_empty_database_returns_empty_list(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_basic_profit_calculation(self):
        """profit = (unit_price - average_cost) * qty = (10 - 6) * 10 = 40"""
        p = self._product("Widget", "W-1", avg_cost="6.00")
        self._sale(p, 10, unit_price="10.00", average_cost="6.00")
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("10"))
        self.assertEqual(Decimal(row["net_revenue"]), Decimal("100.00"))
        self.assertEqual(Decimal(row["total_cost_value"]), Decimal("60.00"))
        self.assertEqual(Decimal(row["profit"]), Decimal("40.00"))

    def test_returns_reduce_profit_correctly(self):
        """Returns reduce both revenue and COGS. Net profit on 7 units."""
        p = self._product("Widget", "W-1", avg_cost="6.00")
        self._sale(p, 10, unit_price="10.00", average_cost="6.00")
        self._return(p, 3, unit_price="10.00", average_cost="6.00")
        data = self.client.get(self.url).json()
        row = data[0]
        self.assertEqual(Decimal(row["quantity_sold"]), Decimal("7"))
        self.assertEqual(Decimal(row["net_revenue"]), Decimal("70.00"))
        self.assertEqual(Decimal(row["total_cost_value"]), Decimal("42.00"))
        self.assertEqual(Decimal(row["profit"]), Decimal("28.00"))

    def test_fully_returned_product_excluded(self):
        p = self._product("Widget", "W-1", avg_cost="6.00")
        self._sale(p, 5, unit_price="10.00", average_cost="6.00")
        self._return(p, 5, unit_price="10.00", average_cost="6.00")
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_unreceived_sale_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 10, is_received=False)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_unreceived_return_not_subtracted(self):
        """Unreceived returns must not reduce profit."""
        p = self._product("Widget", "W-1", avg_cost="5.00")
        self._sale(p, 10, unit_price="10.00", average_cost="5.00")
        self._return(p, 4, unit_price="10.00", average_cost="5.00", is_received=False)
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["quantity_sold"]), Decimal("10"))
        self.assertEqual(Decimal(data[0]["profit"]), Decimal("50.00"))

    def test_deleted_sale_order_excluded(self):
        p = self._product("Widget", "W-1")
        order = self._sale(p, 5)
        order.deleted = True
        order.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_deleted_product_excluded(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        p.deleted = True
        p.save()
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_sorted_by_profit_descending(self):
        p1 = self._product("LowMargin", "L-1", avg_cost="9.00")
        p2 = self._product("HighMargin", "H-1", avg_cost="1.00")
        p3 = self._product("MidMargin", "M-1", avg_cost="5.00")
        self._sale(p1, 10, unit_price="10.00", average_cost="9.00")
        self._sale(p2, 10, unit_price="10.00", average_cost="1.00")
        self._sale(p3, 10, unit_price="10.00", average_cost="5.00")
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["HighMargin", "MidMargin", "LowMargin"])

    def test_tie_broken_by_name_ascending(self):
        p1 = self._product("Zebra", "Z-1", avg_cost="5.00")
        p2 = self._product("Apple", "AP-1", avg_cost="5.00")
        self._sale(p1, 10, unit_price="10.00", average_cost="5.00")
        self._sale(p2, 10, unit_price="10.00", average_cost="5.00")
        names = [d["product"]["name"] for d in self.client.get(self.url).json()]
        self.assertEqual(names, ["Apple", "Zebra"])

    def test_top_10_limit_enforced(self):
        for i in range(15):
            p = self._product(f"Product{i:02d}", f"SKU-{i:02d}", avg_cost=str(i))
            self._sale(p, 10, unit_price="20.00", average_cost=str(i))
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 10)

    def test_top_10_contains_highest_profit_products(self):
        products_profits = []
        for i in range(15):
            avg_cost = str(i)
            p = self._product(f"Product{i:02d}", f"SKU-{i:02d}", avg_cost=avg_cost)
            self._sale(p, 10, unit_price="20.00", average_cost=avg_cost)
            profit = (Decimal("20.00") - Decimal(avg_cost)) * 10
            products_profits.append((p, profit))
        data = self.client.get(self.url).json()
        returned_names = {d["product"]["name"] for d in data}
        top_10 = {p.name for p, _ in sorted(products_profits, key=lambda x: -x[1])[:10]}
        self.assertEqual(returned_names, top_10)

    def test_avg_unit_cost_price_calculation(self):
        p = self._product("Widget", "W-1", avg_cost="6.00")
        self._sale(p, 10, unit_price="10.00", average_cost="6.00")
        data = self.client.get(self.url).json()
        self.assertEqual(Decimal(data[0]["avg_unit_cost_price"]), Decimal("6.00"))

    def test_multiple_products_returns_accounted_independently(self):
        p1 = self._product("Widget", "W-1", avg_cost="5.00")
        p2 = self._product("Gadget", "G-1", avg_cost="3.00")
        self._sale(p1, 10, unit_price="10.00", average_cost="5.00")
        self._sale(p2, 10, unit_price="10.00", average_cost="3.00")
        self._return(p1, 2, unit_price="10.00", average_cost="5.00")
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 2)
        p1_row = next(d for d in data if d["product"]["name"] == "Widget")
        p2_row = next(d for d in data if d["product"]["name"] == "Gadget")
        self.assertEqual(Decimal(p1_row["quantity_sold"]), Decimal("8"))
        self.assertEqual(Decimal(p2_row["quantity_sold"]), Decimal("10"))
        self.assertEqual(Decimal(p1_row["profit"]), Decimal("40.00"))
        self.assertEqual(Decimal(p2_row["profit"]), Decimal("70.00"))

    def test_return_only_product_excluded(self):
        """A product with only returns (no sales) must be excluded."""
        p = self._product("Widget", "W-1")
        self._return(p, 5)
        self.assertEqual(self.client.get(self.url).json(), [])

    def test_response_structure_has_required_fields(self):
        p = self._product("Widget", "W-1")
        self._sale(p, 5)
        row = self.client.get(self.url).json()[0]
        self.assertIn("product", row)
        self.assertIn("quantity_sold", row)
        self.assertIn("net_revenue", row)
        self.assertIn("total_cost_value", row)
        self.assertIn("profit", row)
        self.assertIn("avg_unit_cost_price", row)
