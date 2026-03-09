from django_filters import rest_framework as filters
from ..sales.models import SaleOrder


class SalesFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = SaleOrder
        fields = ["start_date", "end_date"]
