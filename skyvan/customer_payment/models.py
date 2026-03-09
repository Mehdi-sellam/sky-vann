from django.db import models
from core.models import BaseModel, UserAuthorModel
from django.conf import settings
from decimal import Decimal
from sales.models import SaleOrder
from customer.models import Customer
from return_sales.models import ReturnSaleOrder
from .enum import *


class CustomerPayment(UserAuthorModel, BaseModel):

    uuid = models.UUIDField(primary_key=True, unique=True)
    sale = models.ForeignKey(SaleOrder,on_delete=models.SET_NULL, null=True,blank=True, related_name="sale_payments") 
    return_sale_order = models.ForeignKey(ReturnSaleOrder,on_delete=models.SET_NULL, null=True,blank=True, related_name="return_sale_payments")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_payment')
    old_balance = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    amount = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    new_balance = models.DecimalField(max_digits=settings.DEFAULT_MAX_DIGITS,decimal_places=settings.DEFAULT_DECIMAL_PLACES,default=Decimal("0.0"),)
    note = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=PaymentTypeEnum.choices(), default=PaymentTypeEnum.PAYMENT.value)
    method = models.CharField(max_length=20,choices=PaymentMethods.choices(),default=PaymentMethods.CASH.value, )

    def __str__(self):
            return f"{self.type.capitalize()} - {self.amount} ({self.method}) for {self.customer.name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['amount']),
            models.Index(fields=['customer']),
            models.Index(fields=['type']),
            models.Index(fields=['created_at']),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
        ]

