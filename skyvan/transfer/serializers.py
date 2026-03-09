from rest_framework import serializers
from product.serializers import ProductSerializerCustom
from van.serializers import VanSerializerMinInfo
from warehouse.serializers import WarehouseSerializerMinInfo
from .models import Transfer, TransferLine
from account.serializers import UserAuthorSerializer
from account.serializers import UserAuthorBaseSerializer
from .enum import TransferStatus
from .error_codes import TransferErrorCode
from rest_framework.exceptions import ValidationError


class RejectTransferSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class TransferSerializer(UserAuthorBaseSerializer):
    source_van = VanSerializerMinInfo()
    destination_van = VanSerializerMinInfo()
    source_warehouse = WarehouseSerializerMinInfo()
    destination_warehouse = WarehouseSerializerMinInfo()
    status = serializers.ChoiceField(choices=TransferStatus.CHOICES, required=False)

    class Meta:
        model = Transfer
        fields = [
            "uuid",
            "created_by",
            "updated_by",
            "rejection_reason",
            "transfer_type",
            "status",
            "source_van",
            "destination_van",
            "source_warehouse",
            "destination_warehouse",
            "created_at",
            "updated_at",
            "last_synced_at",
        ]


class TransferLineSerializer(serializers.ModelSerializer):
    product =  ProductSerializerCustom()  
    class Meta:
        model = TransferLine
        fields = ["uuid", "product", "quantity"]


class TransferLineCreateSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = TransferLine
        fields = ["uuid", "product", "quantity"]

class CreateTransferSerializer(serializers.ModelSerializer):
    lines = TransferLineCreateSerializer(many=True)  # Accept transfer lines in the request

    class Meta:
        model = Transfer
        fields = [
            "uuid",
            "transfer_type",
            "source_van",
            "destination_van",
            "source_warehouse",
            "destination_warehouse",
            "lines",
        ]

    def validate(self, data):
        source_van = data.get("source_van")
        source_warehouse = data.get("source_warehouse")
        dest_van = data.get("destination_van")
        dest_warehouse = data.get("destination_warehouse")
        # Validate only one source
        if bool(source_van) == bool(source_warehouse):
            raise ValidationError(
                {
                    "code": TransferErrorCode.INVALID.value,
                    "message": "Specify exactly one source: source_van or source_warehouse.",
                    "field": "source",
                }
            )

        # Validate only one destination
        if bool(dest_van) == bool(dest_warehouse):
            raise ValidationError(
                {
                    "code": TransferErrorCode.INVALID.value,
                    "message": "Specify exactly one destination: destination_van or destination_warehouse.",
                    "field": "destination",
                }
            )
        return data


class UpdateTransferSerializer(serializers.ModelSerializer):
    lines = TransferLineCreateSerializer(many=True)  # Accept transfer lines in the request

    class Meta:
        model = Transfer
        fields = [
            "transfer_type",
            "source_van",
            "destination_van",
            "source_warehouse",
            "destination_warehouse",
            "lines",
        ]

    def validate(self, data):
        source_van = data.get("source_van", None)
        source_warehouse = data.get("source_warehouse", None)
        dest_van = data.get("destination_van", None)
        dest_warehouse = data.get("destination_warehouse", None)
        # Validate only one source
        if bool(source_van) == bool(source_warehouse):
            raise ValidationError(
                {
                    "code": "invalid_source",
                    "message": "Specify exactly one source: source_van or source_warehouse.",
                    "field": "source",
                }
            )

        # Validate only one destination
        if bool(dest_van) == bool(dest_warehouse):
            raise ValidationError(
                {
                    "code": TransferErrorCode.INVALID.value,
                    "message": "Specify exactly one destination: destination_van or destination_warehouse.",
                    "field": "destination",
                }
            )
        return data




class MyTransferSerializer(serializers.ModelSerializer):
    lines = TransferLineSerializer(many=True, read_only=True)
    source_van = VanSerializerMinInfo(allow_null=True)
    destination_van = VanSerializerMinInfo(allow_null=True)
    source_warehouse = WarehouseSerializerMinInfo(allow_null=True)
    destination_warehouse = WarehouseSerializerMinInfo(allow_null=True)
    status = serializers.ChoiceField(choices=TransferStatus.CHOICES, required=False)
    updated_by = UserAuthorSerializer(read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "uuid",
            "updated_by",
            "rejection_reason",
            "transfer_type",
            "status",
            "source_van",
            "destination_van",
            "source_warehouse",
            "destination_warehouse",
            "created_at",
            "updated_at",
            "last_synced_at",
            'lines',
        ]
