from rest_framework import serializers

from account.serializers import UserAuthorBaseSerializer
from  supplier.serializers import *
from .models import *



class PurchaseOrderSerializerForPayment(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields  = ['uuid','total_price']
class ReturnPurchaseOrderSerializerForPayment(serializers.ModelSerializer):
    class Meta:
        model = ReturnPurchaseOrder
        fields  = ['uuid','total_price']
# Full Serializer for SupplierPayment

class SupplierPaymentSerializer(UserAuthorBaseSerializer):
    supplier = SupplierSerializerForPayment()
    purchase = PurchaseOrderSerializerForPayment()
    return_purchase_order = ReturnPurchaseOrderSerializerForPayment()
    class Meta:
        model = SupplierPayment
        fields = '__all__'

class SupplierPaymentSerializerForPurchases(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['uuid','amount','note','method','type','old_balance','new_balance']
        
class SupplierPaymentSerializerForReturnPurchases(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['uuid','amount','note','method','type','old_balance','new_balance']
        
# Serializer for Creating SupplierPayment
class CreateSupplierPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['uuid', 'supplier','purchase' ,'return_purchase_order','amount', 'note', 'type','method']

class CreateSupplierPaymentSerializerForPurchases(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = [ 'uuid','supplier','amount', 'note','method']

class CreateSupplierPaymentSerializerForReturnPurchases (serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['uuid','supplier','amount', 'note','method']

class UpdateSupplierPaymentSerializerForPurchases(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['amount', 'note', 'type','method',]
        
class UpdateSupplierPaymentSerializerForReturnPurchases(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['amount', 'note', 'type','method']

# Serializer for Updating SupplierPayment
class UpdateSupplierPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ['amount', 'note', 'type','method']



