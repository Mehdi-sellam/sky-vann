from rest_framework import serializers
from product.models import Product
from account.serializers import UserAuthorBaseSerializer
from warehouse.models import Warehouse
from .models import ReturnPurchaseOrder, ReturnPurchaseLine
from .error_codes import ReturnPurchaseOrderErrorCode
from product.serializers import ProductSerializerForLines
from supplier.serializers import SupplierSerializerFroReturnPurchase
from warehouse.serializers import WarehouseSerializerFroReturnPurchase
from supplier_payment.serializers import *
from supplier_payment.services import *
from supplier_payment.enum import *
from drf_spectacular.utils import extend_schema_field


class ReturnPurchaseLineSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()  # Nested serializer for product details

    class Meta:
        model = ReturnPurchaseLine
        fields = [
            "uuid",
            "product",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
            "created_at",
            "last_synced_at",
        ]


class ReturnPurchaseOrderSerializer(UserAuthorBaseSerializer):
    supplier = SupplierSerializerFroReturnPurchase()
    warehouse = WarehouseSerializerFroReturnPurchase()

    # Use SerializerMethodField to handle custom logic for fetching payments
    payments = serializers.SerializerMethodField()

    class Meta:
        model = ReturnPurchaseOrder
        fields = "__all__"
    @extend_schema_field(SupplierPaymentSerializerForReturnPurchases)
    def get_payments(self, obj):
        # Fetch the first payment related to the product
        payment = SupplierPayment.objects.filter(return_purchase_order=obj).first()
        if payment:
            # Return the serialized payment object
            return SupplierPaymentSerializerForReturnPurchases(payment).data

        # If no related payment, return None
        return None


class CreateReturnPurchaseLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnPurchaseLine
        fields = ["uuid", "product", "quantity", "unit_price", "discount_price"]

    def validate(self, data):
        """
        Ensure the discount does not exceed the unit price.
        """
        if data["discount_price"] > data["unit_price"]:
            raise serializers.ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.INVALID.value,
                    "message": "Discount price cannot exceed unit price.",
                    "field": "discount_price",
                }
            )
        return data


class CreateReturnPurchaseOrderSerializer(serializers.ModelSerializer):
    lines = CreateReturnPurchaseLineSerializer(many=True)
    supplier_payment = CreateSupplierPaymentSerializerForReturnPurchases()

    class Meta:
        model = ReturnPurchaseOrder
        fields = [
            "uuid",
            "date",
            "supplier",
            "warehouse",
            "discount_price",
            "is_received",
            "lines",
            "supplier_payment",
        ]

    def validate_warehouse(self, value):
        """
        Check if the specified warehouse exists or meets certain conditions.
        """
        if not Warehouse.objects.filter(uuid=value.uuid).exists():
            raise serializers.ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": "Warehouse not found.",
                    "field": "warehouse",
                }
            )
        return value


class UpdateReturnPurchaseOrderSerializer(serializers.ModelSerializer):
    lines = CreateReturnPurchaseLineSerializer(many=True)
    supplier_payment = UpdateSupplierPaymentSerializerForReturnPurchases()

    class Meta:
        model = ReturnPurchaseOrder
        fields = [
            "date",
            "supplier",
            "warehouse",
            "is_received",
            "discount_price",
            "lines",
            "supplier_payment",
        ]


class ReturnPurchaseOrderSimpleSerializer(UserAuthorBaseSerializer):
    supplier = SupplierSimpleSerializer()
    warehouse = WarehouseSerializerFroReturnPurchase()

    class Meta:
        model = ReturnPurchaseOrder
        fields = ["uuid", "created_by", "updated_by", "date", "supplier", "warehouse", "number", "created_at"]


class ReturnPurchaseLineReportDetailedSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()
    return_purchase_order = ReturnPurchaseOrderSimpleSerializer()

    class Meta:
        model = ReturnPurchaseLine
        fields = [
            "uuid",
            "product",
            "return_purchase_order",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
        ]


class ReturnPurchaseLineReportSerializer(serializers.Serializer):
    results = ReturnPurchaseLineReportDetailedSerializer(many=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
