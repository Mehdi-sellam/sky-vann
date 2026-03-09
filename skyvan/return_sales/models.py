from django.db import models
from product.models import Product
from core.models import BaseModel, UserAuthorModel
from django.conf import settings
from decimal import Decimal
from customer.models import Customer
from warehouse.models import Warehouse


def get_next_order_number():
    last_order = ReturnSaleOrder.objects.all().order_by("number").last()
    if last_order:
        return last_order.number + 1
    return 1


class ReturnSaleOrder(BaseModel, UserAuthorModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="return_sale_orders"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="return_sale_warehouse"
    )
    date = models.DateField(null=True, blank=True)
    is_received = models.BooleanField(default=False)
    discount_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    number = models.PositiveIntegerField(default=get_next_order_number, unique=True)
    undiscount_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    total_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    def recalculate_totals(self):
        self.undiscount_price = sum(line.total_price for line in self.lines.filter(deleted=False))
        self.total_price = self.undiscount_price - self.discount_price
        self.save(update_fields=["total_price", "undiscount_price"])

    def __str__(self):
        return f"Order from {self.customer.name} at {self.created_at.strftime('%Y-%m-%d')} in {self.warehouse.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["warehouse"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
        ]


class ReturnSaleLine(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    return_sale_order = models.ForeignKey(
        ReturnSaleOrder, related_name="lines", on_delete=models.CASCADE
    )

    product = models.ForeignKey(Product,related_name="return_sale_lines", on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    unit_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    discount_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    undiscount_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    cost_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
        default=Decimal("0.0"),
    )
    average_cost = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
        default=Decimal("0.0"),
    )
    total_price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )

    def save(self, *args, **kwargs):
        # Ensure all fields involved in calculations are Decimals
        self.quantity = (
            Decimal(self.quantity)
            if not isinstance(self.quantity, Decimal)
            else self.quantity
        )
        self.unit_price = (
            Decimal(self.unit_price)
            if not isinstance(self.unit_price, Decimal)
            else self.unit_price
        )
        self.discount_price = (
            Decimal(self.discount_price)
            if not isinstance(self.discount_price, Decimal)
            else self.discount_price
        )

        # Perform calculations safely
        self.undiscount_price = self.unit_price * self.quantity
        self.total_price = self.undiscount_price - self.discount_price

        super().save(*args, **kwargs)

        if self.return_sale_order:
            self.return_sale_order.recalculate_totals()

    def __str__(self):
        return f"{self.quantity} of {self.product.name} at ${self.unit_price} each, discount ${self.discount_price}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["product"]),
        ]
