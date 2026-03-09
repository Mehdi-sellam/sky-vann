from django.db import models
from product.models import Product
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid


from core.models import BaseModel
class Warehouse(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)


class Inventory(BaseModel):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory')
    logical_quantity =  models.DecimalField(max_digits=10, decimal_places=2,default=0)
    physical_quantity =  models.DecimalField(max_digits=10, decimal_places=2,default=0)
    threshold = models.DecimalField(max_digits=10, decimal_places=2,default=0)


class CentralInventory(BaseModel):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    logical_quantity = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    physical_quantity = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    threshold = models.DecimalField(max_digits=10, decimal_places=2,default=0)


class StockHistory(BaseModel):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    date = models.DateTimeField(auto_now_add=True)
    # Represents the source of the stock movement (e.g., warehouse, van)
    source = models.CharField(max_length=100)
    # Represents the ID of the source (e.g., warehouse UUID, van UUID)
    source_id = models.UUIDField()
    # Represents the destination of the stock movement (e.g., warehouse, van)
    destination = models.CharField(max_length=100, blank=True, null=True)
    # Represents the ID of the destination (e.g., warehouse UUID, van UUID)
    destination_id = models.UUIDField(blank=True, null=True)
    action_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    action_id = models.UUIDField()
    action_object = GenericForeignKey('action_type', 'action_id')
    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.product.name} - {self.date}"
