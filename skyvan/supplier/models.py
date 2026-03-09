from django.db import models
from django.core.validators import EmailValidator
from core.models import BaseModel
from decimal import Decimal
from django.conf import settings


class Supplier(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        validators=[EmailValidator(message="Invalid email address.")],
    )
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    balance_init = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    balance = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
