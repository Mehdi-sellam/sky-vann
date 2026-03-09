from rest_framework import serializers
from customer.serializers import *
from account.serializers import UserAuthorBaseSerializer, UserAuthorSerializer
from .models import *


class SaleOrderSerializerForPayment(serializers.ModelSerializer):
    class Meta:
        model = SaleOrder
        fields  = ['uuid','total_price']

class ReturnSaleOrderSerializerForPayment(serializers.ModelSerializer):
    class Meta:
        model = ReturnSaleOrder
        fields  = ['uuid','total_price']

# Full Serializer for CustomerPayment
class CustomerPaymentSerializer(UserAuthorBaseSerializer):
    customer = CustomerSerializerForPayment()
    sale = SaleOrderSerializerForPayment()
    return_sale_order = ReturnSaleOrderSerializerForPayment()
    class Meta:
        model = CustomerPayment
        fields = '__all__'

class CustomerPaymentSerializerForSale(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['uuid','amount','note','method','type','old_balance','new_balance']

class CustomerPaymentSerializerForReturnSale(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['uuid','amount','note','method','type','old_balance','new_balance']

# Serializer for Creating CustomerPayment

class CreateCustomerPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['uuid', 'customer', 'sale', 'return_sale_order', 'amount', 'note', 'type','method']

class CreateCustomerPaymentSerializerForSales(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = [ 'uuid','customer','amount', 'note','method']

class CreateCustomerPaymentSerializerForReturnSales(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = [ 'uuid','customer','amount', 'note','method']

class UpdateCustomerPaymentSerializerForSales(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['amount', 'note', 'type','method']

class UpdateCustomerPaymentSerializerForReturnSales(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['amount', 'note', 'type','method']

# Serializer for Updating CustomerPayment
class UpdateCustomerPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPayment
        fields = ['amount', 'note', 'type','method']


# Status Serializer 
class StatusSerializer(UserAuthorBaseSerializer):
    customer = CustomerSerializerForPayment()
    sale = SaleOrderSerializerForPayment()
    return_sale_order = ReturnSaleOrderSerializerForPayment()
    class Meta:
        model = CustomerPayment
        fields = '__all__'



