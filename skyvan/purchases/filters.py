from django.contrib.auth import get_user_model
import uuid
from warehouse.models import Warehouse
from .error_codes import PurchaseOrderErrorCode
from rest_framework.exceptions import ValidationError
import django_filters
from .models import PurchaseOrder, PurchaseLine, Product, Supplier
from .error_codes import PurchaseOrderErrorCode


class UUIDValidationMixin:
    def _check_uuid_exists(self, model, value, field_label):
        """Generic lightweight existence check"""
        if not model.objects.filter(uuid=value).exists():
            raise ValidationError({
                "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"{field_label} with UUID {value} not found.",
                "field": field_label.lower().replace(" ", "_"),
            })

    def validate_author_created_by_or_updated_by(self, queryset, name, value):
        """check for author created_by or updated_by"""
        self._check_uuid_exists(get_user_model(), value, "User")
        return queryset.filter(**{name: value})

    def validate_warehouse(self, queryset, name, value):
        # Use set comprehension to remove duplicates immediately
        raw_uuids = list(set(u.strip() for u in value.split(",") if u.strip()))
        
        # Validate format
        valid_uuids = []
        for item in raw_uuids:
            try:
                uuid.UUID(item)
                valid_uuids.append(item)
            except ValueError:
                raise ValidationError({"code": "INVALID_FORMAT", "message": f"Invalid UUID: {item}"})

        # Bulk existence check
        found_count = Warehouse.objects.filter(uuid__in=valid_uuids).count()
        if found_count != len(valid_uuids):
            raise ValidationError({
                "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                "message": "One or more warehouse UUIDs are invalid or missing.",
            })   
        return queryset.filter(**{name: valid_uuids})


class PurchaseOrderFilter(UUIDValidationMixin, django_filters.FilterSet):
    min_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    max_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    supplier = django_filters.CharFilter(
        field_name="supplier__name", lookup_expr="icontains"
    )
    is_received = django_filters.BooleanFilter(field_name="is_received")
    number = django_filters.NumberFilter(field_name="number")
    warehouse = django_filters.CharFilter(field_name="warehouse__uuid__in", method="validate_warehouse", label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's")
    created_by = django_filters.UUIDFilter(field_name="created_by__uuid", method="validate_author_created_by_or_updated_by", label="filter by who created the record by created_by uuid")
    updated_by = django_filters.UUIDFilter(field_name="updated_by__uuid", method="validate_author_created_by_or_updated_by", label="filter by who last updated the record by updated_by uuid")

    class Meta:
        model = PurchaseOrder
        fields = ["min_date", "max_date", "supplier", "is_received", "number", "warehouse", "created_by", "updated_by"]

        


class PurchaseLineReportFilter(UUIDValidationMixin, django_filters.FilterSet):
    supplier_uuid = django_filters.UUIDFilter(
        field_name="purchase_order__supplier__uuid", method="validate_supplier_uuid"
    )
    product_uuid = django_filters.UUIDFilter(
        field_name="product__uuid", method="validate_product_uuid"
    )
    date = django_filters.DateFromToRangeFilter(field_name="purchase_order__date")
    warehouse = django_filters.CharFilter(
        field_name="warehouse__uuid__in", 
        method="validate_warehouse", 
        label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's"
    )
    created_by = django_filters.UUIDFilter(
        field_name="created_by__uuid", 
        method="validate_author_created_by_or_updated_by", 
        label="filter by who created the record by created_by uuid"
    )
    updated_by = django_filters.UUIDFilter(
        field_name="updated_by__uuid", 
        method="validate_author_created_by_or_updated_by",
        label="filter by who last updated the record by updated_by uuid"
    )

    class Meta:
        model = PurchaseLine
        fields = ["supplier_uuid", "warehouse", "product_uuid", "date", "created_by", "updated_by"]

    def validate_supplier_uuid(self, queryset, name, value):
        """Validate that the provided supplier UUID exists"""
        if not Supplier.objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": f"Supplier with UUID {value} not found.",
                    "field": "supplier_uuid",
                }
            )
        return queryset.filter(**{name: value})

    def validate_product_uuid(self, queryset, name, value):
        """Validate that the provided product UUID exists"""
        if not Product.objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": f"Product with UUID {value} not found.",
                    "field": "product_uuid",
                }
            )
        return queryset.filter(**{name: value})
