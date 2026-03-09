import django_filters
from django.contrib.auth import get_user_model

from warehouse.models import Warehouse
from .models import ReturnSaleOrder, ReturnSaleLine
from customer.models import Customer
from product.models import Product
from rest_framework.exceptions import ValidationError
from .error_codes import ReturnSaleOrderErrorCode


class ReturnSaleOrderFilter(django_filters.FilterSet):
    min_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    max_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    customer = django_filters.CharFilter(
        field_name="customer__name", lookup_expr="icontains"
    )
    is_received = django_filters.BooleanFilter(field_name="is_received")
    number = django_filters.NumberFilter(field_name="number")
    warehouse = django_filters.CharFilter(field_name="warehouse__uuid__in", method="validate_warehouse", label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's")
    created_by = django_filters.UUIDFilter(field_name="created_by__uuid", method="validate_created_by", label= "filter by Created By UUID")
    updated_by = django_filters.UUIDFilter(field_name="updated_by__uuid", method="validate_updated_by", label= "filter by Updated By UUID")

    class Meta:
        model = ReturnSaleOrder
        fields = ["min_date", "max_date", "customer", "is_received", "number", "warehouse", "created_by", "updated_by"]

    def validate_created_by(self, queryset, name, value):
        """Validate that the provided created_by UUID exists"""
        if not get_user_model().objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
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
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
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
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": f"Warehouse with warehouse UUID {', '.join(uuids)} not found.",
                    "field": "warehouse",
                }
            )
        return queryset.filter(**{name: value})

class ReturnSaleLineReportFilter(django_filters.FilterSet):
    customer_uuid = django_filters.UUIDFilter(
        field_name="return_sale_order__customer__uuid", method="validate_customer_uuid"
    )
    product_uuid = django_filters.UUIDFilter(
        field_name="product__uuid", method="validate_product_uuid"
    )
    date = django_filters.DateFromToRangeFilter(
        field_name="return_sale_order__date"
    )
    warehouse = django_filters.CharFilter(
        field_name="warehouse__uuid__in", method="validate_warehouse", label= "filter by Warehouse UUID, make sure to include commas ',' between UUID's"
    )
    created_by = django_filters.UUIDFilter(
        field_name="created_by__uuid", method="validate_created_by", label= "filter by Created By UUID")
    updated_by = django_filters.UUIDFilter(
        field_name="updated_by__uuid", method="validate_updated_by", label= "filter by Updated By UUID"
    )


    class Meta:
        model = ReturnSaleLine
        fields = ["customer_uuid", "product_uuid", "date"]

    def validate_customer_uuid(self, queryset, name, value):
        """Validate that the provided customer UUID exists"""
        if not Customer.objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": f"Customer with UUID {value} not found.",
                    "field": "customer_uuid",
                }
            )
        return queryset.filter(**{name: value})

    def validate_product_uuid(self, queryset, name, value):
        """Validate that the provided product UUID exists"""
        if not Product.objects.filter(uuid=value).exists():
            raise ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": f"Product with UUID {value} not found.",
                    "field": "product_uuid",
                }
            )
        return queryset.filter(**{name: value})
    
    def validate_warehouse(self, queryset, name, value):
        uuids =[uuid.strip() for uuid in value.split(",")] 
     
        """Validate that the provided warehouse UUID exists"""
        if not Warehouse.objects.filter(uuid__in=uuids).exists():
            raise ValidationError(
                {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": f"Warehouse with warehouse UUID {', '.join(uuids)} not found.",
                    "field": "warehouse",
                }
            )
        return queryset.filter(**{name: value})
