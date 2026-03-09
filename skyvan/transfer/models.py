from django.db import models
from product.models import Product
from .enum import TransferType, TransferStatus
from warehouse.models import Warehouse
from van.models import Van
from core.models import BaseModel, UserAuthorModel
from django.conf import settings


class TransferLine(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    transfer = models.ForeignKey(
        "Transfer", on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="transfer_lines")
    quantity = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    def __str__(self):
        return f"Transfer Line - {self.pk}"


class Transfer(BaseModel, UserAuthorModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    transfer_type = models.CharField(max_length=30, choices=TransferType.CHOICES)
    source_van = models.ForeignKey(
        Van, on_delete=models.CASCADE, blank=True, null=True, related_name="source_van"
    )
    destination_van = models.ForeignKey(
        Van,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="destination_van",
    )
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="source_warehouse",
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="destination_warehouse",
    )
    status = models.CharField(
        max_length=20,
        choices=TransferStatus.CHOICES,
        default=TransferStatus.PENDING,
    )
    rejection_reason = models.CharField(max_length=200, blank=True, null=True)
    reversed_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"Transfer - {self.pk}"
