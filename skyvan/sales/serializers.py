from rest_framework import serializers
from product.models import Product

from warehouse.models import Warehouse
from .models import SaleOrder, SaleLine
from .error_codes import SaleOrderErrorCode
from product.serializers import ProductSerializerForLines
from customer.serializers import CustomerSerializerFroSale, CustomerSimpleSerializer
from warehouse.serializers import WarehouseSerializerFroSale, WarehouseSerializerMinInfo
from van.serializers import VanSerializerMinInfo
from account.serializers import UserAuthorBaseSerializer, UserAuthorSerializer
from customer_payment.models import CustomerPayment
from customer_payment.serializers import (
    CreateCustomerPaymentSerializerForSales,
    UpdateCustomerPaymentSerializerForSales,
    CustomerPaymentSerializerForSale,
    
)  
from drf_spectacular.utils import extend_schema_field


class CreateSaleLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLine
        fields = ["uuid", "product", "quantity", "unit_price", "discount_price"]

    def validate(self, data):
        if data["discount_price"] > data["unit_price"]:
            raise serializers.ValidationError(
                {
                    "code": SaleOrderErrorCode.INVALID.value,
                    "message": "Discount price cannot exceed unit price.",
                    "field": "discount_price",
                }
            )

        return data


class CreateSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateSaleLineSerializer(many=True)
    customer_payment = CreateCustomerPaymentSerializerForSales()

    class Meta:
        model = SaleOrder
        fields = [
            "uuid",
            "date",
            "customer",
            "warehouse",
            "discount_price",
            "is_received",
            "lines",
            "customer_payment",
        ]


class UpdateSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateSaleLineSerializer(many=True)
    customer_payment = UpdateCustomerPaymentSerializerForSales()

    class Meta:
        model = SaleOrder
        fields = [
            "date",
            "customer",
            "warehouse",
            "is_received",
            "discount_price",
            "lines",
            "customer_payment",
        ]


class UpdateVanSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateSaleLineSerializer(many=True)
    customer_payment = UpdateCustomerPaymentSerializerForSales()

    class Meta:
        model = SaleOrder
        fields = [
            "date",
            "customer",
            "van",
            "is_received",
            "discount_price",
            "lines",
            "customer_payment",
        ]


class SaleLineSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()  # Nested serializer for product details

    class Meta:
        model = SaleLine
        fields = [
            "uuid",
            "product",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
            "cost_price",
            "average_cost",
            "created_at",
            "last_synced_at",
        ]


class SaleOrderSerializer(UserAuthorBaseSerializer):
    customer = CustomerSerializerFroSale()
    warehouse = WarehouseSerializerMinInfo()
    van = VanSerializerMinInfo() 
    payments = serializers.SerializerMethodField()

    class Meta:
        model = SaleOrder
        fields = "__all__"
    @extend_schema_field(CustomerPaymentSerializerForSale)
    def get_payments(self, obj):
        # Fetch the first payment related to the product
        payment = CustomerPayment.objects.filter(sale=obj).first()
        if payment:
            # Return the serialized payment object
            return CustomerPaymentSerializerForSale(payment).data

        # If no related payment, return None
        return None


class SaleOrderSimpleSerializer(UserAuthorBaseSerializer):
    customer = CustomerSimpleSerializer()
    warehouse = WarehouseSerializerFroSale()

    class Meta:
        model = SaleOrder
        fields = ["uuid", "created_by", "updated_by", "date", "customer", "warehouse", "number", "created_at"]


class SaleLineReportDetailedSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()
    sale_order = SaleOrderSimpleSerializer()

    class Meta:
        model = SaleLine
        fields = [
            "uuid",
            "product",
            "sale_order",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
            "cost_price",
            "average_cost",
        ]


class SaleLineReportSerializer(serializers.Serializer):
    results = SaleLineReportDetailedSerializer(many=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CreateVanSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateSaleLineSerializer(many=True)
    customer_payment = CreateCustomerPaymentSerializerForSales()
 
    class Meta:
        model = SaleOrder
        fields = [
            "uuid",
            "date",
            "customer",
            "discount_price",
            "is_received",
            "customer_payment",
            "lines",
        ]


class MySaleOrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializerFroSale()
    warehouse = WarehouseSerializerMinInfo()
    van = VanSerializerMinInfo() 
    payments = serializers.SerializerMethodField()
    updated_by = UserAuthorSerializer(read_only=True)

    class Meta:
        model = SaleOrder
        fields = [
            "uuid",
            "updated_by",
            "customer",
            "warehouse",
            "van",
            "payments",
            "created_at",
            "updated_at",
            "last_synced_at",
            "deleted",
            "date",
            "is_received",
            "discount_price",
            "number",
            "undiscount_price",
            "total_price",
        ]
    @extend_schema_field(CustomerPaymentSerializerForSale)
    def get_payments(self, obj):
        # Fetch the first payment related to the product
        payment = CustomerPayment.objects.filter(sale=obj).first()
        if payment:
            # Return the serialized payment object
            return CustomerPaymentSerializerForSale(payment).data

        # If no related payment, return None
        return None