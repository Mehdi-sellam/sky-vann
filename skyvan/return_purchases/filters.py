import django_filters
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from warehouse.models import Warehouse
from .models import ReturnPurchaseOrder, ReturnPurchaseLine, Product, Supplier
from .error_codes import ReturnPurchaseOrderErrorCode

class UUIDValidationMixin:

    def validate_created_by(self, queryset, name, value):
        """Validate that the provided UUID exists"""
        if not get_user_model().objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
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
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
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
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": f"Warehouse with warehouse UUID {', '.join(uuids)} not found.",
                    "field": "warehouse",
                }
            )
        return queryset.filter(**{name: value})


class ReturnPurchaseOrderFilter(UUIDValidationMixin, django_filters.FilterSet):
    min_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    max_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    supplier = django_filters.CharFilter(field_name="supplier__name", lookup_expr="icontains" )
    is_received = django_filters.BooleanFilter(field_name="is_received")
    number = django_filters.NumberFilter(field_name="number")
    warehouse = django_filters.CharFilter(field_name="warehouse__uuid__in", method="validate_warehouse", label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's")
    created_by = django_filters.UUIDFilter(field_name="created_by__uuid", method="validate_created_by", label="filter by who created the record by created_by uuid")
    updated_by = django_filters.UUIDFilter(field_name="updated_by__uuid", method="validate_updated_by", label="filter by who last updated the record by updated_by uuid")

    class Meta:
        model = ReturnPurchaseOrder
        fields = ["min_date", "max_date", "supplier", "is_received", "number", "warehouse", "created_by", "updated_by"]


class ReturnPurchaseLineReportFilter(UUIDValidationMixin, django_filters.FilterSet):
    supplier_uuid = django_filters.UUIDFilter(
        field_name="return_purchase_order__supplier__uuid",
        method="validate_supplier_uuid",
    )
    product_uuid = django_filters.UUIDFilter(
        field_name="product__uuid", method="validate_product_uuid"
    )
    date = django_filters.DateFromToRangeFilter(
        field_name="return_purchase_order__date"
    )
    warehouse = django_filters.CharFilter(
        field_name="warehouse__uuid__in", 
        method="validate_warehouse", 
        label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's"
    )
    created_by = django_filters.UUIDFilter(
        field_name="created_by__uuid", 
        method="validate_created_by", 
        label="filter by who created the record by created_by uuid"
    )
    updated_by = django_filters.UUIDFilter(
        field_name="updated_by__uuid", 
        method="validate_updated_by", 
        label="filter by who last updated the record by updated_by uuid"
    )

    class Meta:
        model = ReturnPurchaseLine
        fields = ["supplier_uuid", "warehouse", "product_uuid", "date", "created_by", "updated_by"]

    def validate_supplier_uuid(self, queryset, name, value):
        """Validate that the provided supplier UUID exists"""
        if not Supplier.objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
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
                    "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": f"Product with UUID {value} not found.",
                    "field": "product_uuid",
                }
            )
        return queryset.filter(**{name: value})
