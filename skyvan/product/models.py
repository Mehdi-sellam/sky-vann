from django.db import models
from core.models import BaseModel
# Create your models here.
from django.conf import settings
from decimal import Decimal
class Category(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    def __str__(self):
        return self.name

class ProductType(models.TextChoices):
    PHYSICAL = 'Physical', 'Physical Product'
    SERVICE = 'Service', 'Service Product'
    DIGITAL = 'Digital', 'Digital Product'


class Product(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=100, unique=True, null=True)
    price = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        blank=True,
        null=True,
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
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_type = models.CharField(
        max_length=10, choices=ProductType.choices, default=ProductType.PHYSICAL
    )
    # image = models.ImageField(
    #     upload_to='product_images/', blank=True, null=True)
    def __str__(self):
        return self.name

class Barcode(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='barcodes')
    def __str__(self):
        return self.code