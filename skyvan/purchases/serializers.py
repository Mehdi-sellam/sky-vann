from rest_framework import serializers

from account.serializers import UserAuthorBaseSerializer, UserAuthorSerializer
from .models import PurchaseOrder, PurchaseLine
from .error_codes import PurchaseOrderErrorCode
from product.serializers import ProductSerializerForLines
from supplier.serializers import SupplierSerializerFroPurchase
from warehouse.serializers import WarehouseSerializerFroPurchase
from django.conf import settings
from supplier_payment.serializers import (
    CreateSupplierPaymentSerializerForPurchases,
    UpdateSupplierPaymentSerializerForPurchases,
    SupplierPaymentSerializerForPurchases,
)
from supplier.serializers import SupplierSimpleSerializer
from drf_spectacular.utils import extend_schema_field


class CreatePurchaseLineSerializer(serializers.ModelSerializer):
    sale_price = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        required=True,
    )

    class Meta:
        model = PurchaseLine
        fields = [
            "uuid",
            "product",
            "quantity",
            "unit_price",
            "sale_price",
            "discount_price",
        ]

    def validate(self, data):

        if data["discount_price"] > data["unit_price"]:
            raise serializers.ValidationError(
                {
                    "code": PurchaseOrderErrorCode.INVALID.value,
                    "message": "Discount price cannot exceed unit price.",
                    "field": "discount_price",
                }
            )
        return data


class CreatePurchaseOrderSerializer(serializers.ModelSerializer):
    lines = CreatePurchaseLineSerializer(many=True)
    supplier_payment = CreateSupplierPaymentSerializerForPurchases()

    class Meta:
        model = PurchaseOrder
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


class UpdatePurchaseOrderSerializer(serializers.ModelSerializer):
    lines = CreatePurchaseLineSerializer(many=True)
    supplier_payment = UpdateSupplierPaymentSerializerForPurchases()

    class Meta:
        model = PurchaseOrder
        fields = [
            "date",
            "warehouse",
            "is_received",
            "discount_price",
            "lines",
            "supplier_payment",
        ]


class PurchaseLineSerializer(UserAuthorBaseSerializer):
    product = ProductSerializerForLines()  # Nested serializer for product details

    class Meta:
        model = PurchaseLine
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
            "created_by",
            "updated_by",
        ]


class PurchaseOrderSerializer(UserAuthorBaseSerializer):
    supplier = SupplierSerializerFroPurchase()
    warehouse = WarehouseSerializerFroPurchase()

    # Use SerializerMethodField to handle custom logic for fetching payments
    payments = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        
    @extend_schema_field(SupplierPaymentSerializerForPurchases)
    def get_payments(self, obj):
        # Fetch the first payment related to the product

        payment = obj.purchase_payments.filter(deleted=False).first()
        if payment:
            # Return the serialized payment object
            return SupplierPaymentSerializerForPurchases(payment).data

        # If no related payment, return None
        return None


class PurchaseOrderSimpleSerializer(UserAuthorBaseSerializer):
    supplier = SupplierSimpleSerializer()
    warehouse = WarehouseSerializerFroPurchase()

    class Meta:
        model = PurchaseOrder
        fields = ["uuid", "created_by", "updated_by", "date", "supplier", "warehouse", "number", "created_at"]


class PurchaseLineReportDetailedSerializer(serializers.ModelSerializer):
    product = ProductSerializerForLines()
    purchase_order = PurchaseOrderSimpleSerializer()

    class Meta:
        model = PurchaseLine
        fields = [
            "uuid",
            "product",
            "purchase_order",
            "quantity",
            "unit_price",
            "discount_price",
            "undiscount_price",
            "total_price",
        ]


class PurchaseLineReportSerializer(serializers.Serializer):
    results = PurchaseLineReportDetailedSerializer(many=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
