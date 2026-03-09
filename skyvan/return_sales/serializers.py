from rest_framework import serializers
from product.models import Product
from account.serializers import UserAuthorBaseSerializer
from warehouse.models import Warehouse
from .models import ReturnSaleOrder, ReturnSaleLine
from .error_codes import ReturnSaleOrderErrorCode
from product.serializers import ProductSerializerForLines
from customer.serializers import (
    CustomerSerializerFroReturnSale,
    CustomerSimpleSerializer,
)
from warehouse.serializers import WarehouseSerializerFroReturnSale
from customer_payment.serializers import (
    CustomerPaymentSerializerForReturnSale,
    CreateCustomerPaymentSerializerForReturnSales,
    UpdateCustomerPaymentSerializerForReturnSales,
)
from customer_payment.models import CustomerPayment
from drf_spectacular.utils import extend_schema_field


class CreateReturnSaleLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnSaleLine
        fields = ["uuid", "product", "quantity", "unit_price", "discount_price"]

    def validate(self, data):
        if data["discount_price"] > data["unit_price"]:
            raise serializers.ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.INVALID.value,
                    "message": "Discount price cannot exceed unit price.",
                    "field": "discount_price",
                }
            )
        return data


class CreateReturnSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateReturnSaleLineSerializer(many=True)
    customer_payment = CreateCustomerPaymentSerializerForReturnSales()

    class Meta:
        model = ReturnSaleOrder
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


class UpdateReturnSaleOrderSerializer(serializers.ModelSerializer):
    lines = CreateReturnSaleLineSerializer(many=True, required=False)
    customer_payment = UpdateCustomerPaymentSerializerForReturnSales()

    class Meta:
        model = ReturnSaleOrder
        fields = [
            "date",
            "customer",
            "warehouse",
            "is_received",
            "discount_price",
            "lines",
            "customer_payment",
        ]


class ReturnSaleLineSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()

    class Meta:
        model = ReturnSaleLine
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


class ReturnSaleOrderSerializer(UserAuthorBaseSerializer):
    customer = CustomerSerializerFroReturnSale()
    warehouse = WarehouseSerializerFroReturnSale()
    payments = serializers.SerializerMethodField()
    # lines = ReturnSaleLineSerializer(many=True)

    class Meta:
        model = ReturnSaleOrder
        fields = [
            "uuid",
            "created_by",
            "updated_by",
            "customer",
            "warehouse",
            "is_received",
            "discount_price",
            "number",
            "undiscount_price",
            "total_price",
            "date",
            "payments",
            "created_at",
            "updated_at",
            "last_synced_at",
        ]
    @extend_schema_field(CustomerPaymentSerializerForReturnSale)
    def get_payments(self, obj):
        payment = CustomerPayment.objects.filter(return_sale_order=obj).first()
        if payment:
            return CustomerPaymentSerializerForReturnSale(payment).data
        return None


class ReturnSaleOrderSimpleSerializer(UserAuthorBaseSerializer):
    customer = CustomerSimpleSerializer()
    warehouse = WarehouseSerializerFroReturnSale()

    class Meta:
        model = ReturnSaleOrder
        fields = ["uuid", "created_by", "updated_by", "date", "customer", "warehouse", "number", "created_at"]


class ReturnSaleLineReportDetailedSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()
    return_sale_order = ReturnSaleOrderSimpleSerializer()

    class Meta:
        model = ReturnSaleLine
        fields = [
            "uuid",
            "product",
            "return_sale_order",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
            "cost_price",
            "average_cost",
        ]


class ReturnSaleLineReportSerializer(serializers.Serializer):
    results = ReturnSaleLineReportDetailedSerializer(many=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
