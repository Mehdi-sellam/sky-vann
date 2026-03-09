from django.db import models

# Create your models here.
from product.models import Product
from account.models import User
from core.models import BaseModel
from django.utils import timezone
from .enums import VanStatus
import uuid
from decimal import Decimal


class Van(BaseModel):
    uuid = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)  # Example: "Van 1" or "Delivery Van"
    license_plate = models.CharField(max_length=20, unique=True)
    capacity = models.DecimalField(max_digits=10, decimal_places=2)  # in kg or units
    status = models.CharField(
        max_length=20, choices=VanStatus.CHOICES, default=VanStatus.ACTIVE
    )

    def __str__(self):
        return f"{self.name} - {self.license_plate}"


class VanInventory(BaseModel):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    van = models.ForeignKey(Van, on_delete=models.CASCADE, related_name="inventories")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="van_inventories"
    )
    quantity = models.DecimalField(
        max_digits=10, default=Decimal("0.0"), decimal_places=2
    )

    class Meta:
        unique_together = ("van", "product")  # only one record per product per van

    def __str__(self):
        return f"{self.product.name} in {self.van.name}: {self.quantity}"


class VanAssignment(BaseModel):
    uuid = models.UUIDField(primary_key=True)
    van = models.ForeignKey(Van, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="van_assignments"
    )
    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-start_datetime"]

    def __str__(self):
        return f"{self.user.username} assigned to {self.van.name} ({self.start_datetime.date()})"
