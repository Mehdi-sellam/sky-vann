from rest_framework import serializers
from .models import Van, VanAssignment, VanInventory
from .enums import VanStatus
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from account.serializers import OrganizationUserSerializer
from .error_codes import VanErrorCode
from product.serializers import ProductSerializerForInventory


class VanCreateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VanStatus.CHOICES, required=False)

    class Meta:
        model = Van
        fields = ["uuid", "name", "license_plate", "capacity", "status"]


class VanUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=VanStatus.CHOICES, required=False)

    class Meta:
        model = Van
        fields = ["name", "license_plate", "capacity", "status"]


class VanSerializer(serializers.ModelSerializer):
    is_working = serializers.SerializerMethodField()
    status = serializers.ChoiceField(choices=VanStatus.CHOICES)

    class Meta:
        model = Van
        fields = ["uuid", "name", "license_plate", "capacity", "is_working", "status"]

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_working(self, obj):
        return obj.assignments.filter(is_active=True).exists()


class VanSerializerMinInfo(serializers.ModelSerializer):
    class Meta:
        model = Van
        fields = [
            "uuid",
            "name",
            "license_plate",
        ]


class VanAssignmentSerializer(serializers.ModelSerializer):
    van = VanSerializerMinInfo()
    user = OrganizationUserSerializer()

    class Meta:
        model = VanAssignment
        fields = [
            "uuid",
            "van",
            "user",
            "is_active",
            "start_datetime",
            "end_datetime",
            "notes",
        ]


class CreateVanAssignmentSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    van_uuid = serializers.UUIDField()
    user_uuid = serializers.UUIDField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        if data.get("end_datetime") and data["end_datetime"] < data["start_datetime"]:
            raise serializers.ValidationError(
                {"end_datetime": ["End time must be after start time."]}
            )
        return data


class UpdateVanAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VanAssignment
        fields = ["start_datetime", "end_datetime", "notes"]

    def validate(self, data):
        start = data.get("start_datetime") or self.instance.start_datetime
        end = data.get("end_datetime") or self.instance.end_datetime

        if end and end < start:
            raise serializers.ValidationError(
                {
                    "end_datetime": {
                        "code": VanErrorCode.INVALID_DATE_RANGE.value,
                        "message": "End time must be after start time.",
                    }
                }
            )
        return data


class VanInventorySerializer(serializers.ModelSerializer):
    product = ProductSerializerForInventory(
        read_only=True
    )  # include nested product details

    class Meta:
        model = VanInventory
        fields = [
            "uuid",
            "product",
            "quantity",
        ]
