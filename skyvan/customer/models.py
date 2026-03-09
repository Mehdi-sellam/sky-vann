from django.db import models
from django.core.validators import EmailValidator
from core.models import BaseModel
from decimal import Decimal
from django.conf import settings

class Customer(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    balance_init =  models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),)
    balance =  models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),)
    def __str__(self):
        return f"{self.name} "


class Contact(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True, validators=[EmailValidator(message="Invalid email address.")])
    phone = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"
