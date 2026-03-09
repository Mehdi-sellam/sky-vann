from django.db import models
from core.models import BaseModel
from django.conf import settings
from decimal import Decimal


class ExpenseType(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True, )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')

    def __str__(self):
        return self.name

class Expense(BaseModel):
    uuid = models.UUIDField(primary_key=True, unique=True)
    type = models.ForeignKey(ExpenseType, on_delete=models.CASCADE,  related_name='expenses_type')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0.0"),
    )
    date = models.DateField()
    is_recurring = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.description} - {self.amount}"

