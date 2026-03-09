from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from django_filters import rest_framework as filters
from .error_codes import CustomerPaymentErrorCode
from .models import CustomerPayment


class CustomerPaymentFilter(filters.FilterSet):
    min_date = filters.DateFilter(
        field_name="created_at", lookup_expr="gte"
    )  # Filter for transactions created on or after a date
    max_date = filters.DateFilter(
        field_name="created_at", lookup_expr="lte"
    )  # Filter for transactions created on or before a date
    min_amount = filters.NumberFilter(
        field_name="amount", lookup_expr="gte"
    )  # Filter for amounts greater than or equal to a value
    max_amount = filters.NumberFilter(
        field_name="amount", lookup_expr="lte"
    )  # Filter for amounts less than or equal to a value
    type = filters.CharFilter(
        field_name="type", lookup_expr="iexact"
    )  # Exact match for transaction type
    note = filters.CharFilter(
        field_name="note", lookup_expr="icontains"
    )  # Case-insensitive search in notes
    method = filters.CharFilter(field_name="method", lookup_expr="iexact")
    customer_uuid = filters.UUIDFilter(
        field_name="customer__uuid", lookup_expr="iexact"
    )  # Exact match for customer UUID
    created_by = filters.UUIDFilter(
        field_name="created_by__uuid", lookup_expr="iexact", method="validate_created_by",
        label="Filter by the UUID of the user who created the record"
    )  # Exact match for created_by UUID
    updated_by = filters.UUIDFilter(
        field_name="updated_by__uuid", lookup_expr="iexact", method="validate_updated_by",
        label="Filter by the UUID of the user who last updated the record"
    )  # Exact match for updated_by UUID
    class Meta:
        model = CustomerPayment
        fields = [
            "min_date",
            "max_date",
            "min_amount",
            "max_amount",
            "type",
            "note",
            "customer_uuid",
            "method",
            "created_by",
            "updated_by",
        ]


    def validate_created_by(self, queryset, name, value):
        """Validate that the provided created_by UUID exists"""
        if not get_user_model().objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": CustomerPaymentErrorCode.NOT_FOUND.value,
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
                    "code": CustomerPaymentErrorCode.NOT_FOUND.value,
                    "message": f"User with updated_by UUID {value} not found.",
                    "field": "updated_by",
                }
            )
        return queryset.filter(**{name: value})
