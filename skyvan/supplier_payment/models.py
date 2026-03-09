from django.db import models
from core.models import BaseModel, UserAuthorModel
from django.conf import settings
from decimal import Decimal
from purchases.models import PurchaseOrder
from return_purchases.models import ReturnPurchaseOrder
from supplier.models import Supplier
from .enum import *


class SupplierPayment(BaseModel, UserAuthorModel):

    uuid = models.UUIDField(primary_key=True, unique=True)
    purchase = models.ForeignKey(PurchaseOrder,on_delete=models.SET_NULL, null=True,blank=True, related_name="purchase_payments")
    return_purchase_order = models.ForeignKey(ReturnPurchaseOrder,on_delete=models.SET_NULL, null=True,blank=True, related_name="return_purchase_payments")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplier_payment')
    old_balance = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    amount = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    new_balance = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    note = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=PaymentTypes.choices(), default=PaymentTypes.PAYMENT.value)
    method = models.CharField(max_length=20,choices=PaymentMethods.choices(),default=PaymentMethods.CASH.value, )

    def __str__(self):
        return f"{self.type.capitalize()} of {self.amount} for {self.supplier.name} on {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['amount']),
            models.Index(fields=['supplier']),
            models.Index(fields=['type']),
            models.Index(fields=['created_at']),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
        ]

