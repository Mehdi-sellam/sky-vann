import django_filters
from .models import *
from .enum import TransferStatus
from .error_codes import TransferErrorCode
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model


class TransferFilter(django_filters.FilterSet):
    transfer_type = django_filters.CharFilter(
        field_name="transfer_type", lookup_expr="exact"
    )
    source_warehouse = django_filters.UUIDFilter(field_name="source_warehouse__uuid")
    destination_warehouse = django_filters.UUIDFilter(
        field_name="destination_warehouse__uuid"
    )
    source_van = django_filters.UUIDFilter(field_name="source_van__uuid")
    destination_van = django_filters.UUIDFilter(field_name="destination_van__uuid")
    created_at_after = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_at_before = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte"
    )
    updated_at_after = django_filters.DateFilter(
        field_name="updated_at", lookup_expr="gte"
    )
    updated_at_before = django_filters.DateFilter(
        field_name="updated_at", lookup_expr="lte"
    )
    warehouse = django_filters.CharFilter(
        field_name="warehouse__uuid__in", method="validate_warehouse", 
        label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's"
    )
    created_by = django_filters.UUIDFilter(
        field_name="created_by__uuid", method="validate_created_by", 
        label="Filter by the UUID of the user who created the record"
    )
    updated_by = django_filters.UUIDFilter(
        field_name="updated_by__uuid", method="validate_updated_by", 
        label="Filter by the UUID of the user who last updated the record"
    )

    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=TransferStatus.CHOICES,
    )

    def validate_created_by(self, queryset, name, value):
        """Validate that the provided UUID exists"""
        if not get_user_model().objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": TransferErrorCode.NOT_FOUND.value,
                    "message": f"User with created_by UUID {value} not found.",
                    "field": "created_by",
                }
            )
        return queryset.filter(**{name: value})

    def validate_updated_by(self, queryset, name, value):
        """Validate that the provided updated_by UUID exists"""
        if not get_user_model().objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": TransferErrorCode.NOT_FOUND.value,
                    "message": f"User with updated_by UUID {value} not found.",
                    "field": "updated_by",
                }
            )
        return queryset.filter(**{name: value})

    def validate_warehouse(self, queryset, name, value):
        uuids =[uuid.strip() for uuid in value.split(",")] 
     
        """Validate that the provided warehouse UUID exists"""
        if not Warehouse.objects.filter(uuid__in=uuids).exists():
            raise ValidationError(
                {
                    "code": TransferErrorCode.NOT_FOUND.value,
                    "message": f"Warehouse with warehouse UUID {', '.join(uuids)} not found.",
                    "field": "warehouse",
                }
            )
        return queryset.filter(**{name: value})

    class Meta:
        model = Transfer
        fields = [
            "transfer_type",
            "source_warehouse",
            "destination_warehouse",
            "source_van",
            "destination_van",
            "created_at_after",
            "created_at_before",
            "updated_at_after",
            "updated_at_before",
            "status",
            "created_by",
            "updated_by",
        ]
