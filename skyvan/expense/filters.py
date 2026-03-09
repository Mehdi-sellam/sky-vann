from django_filters import rest_framework as filters
from .models import Expense 


class ExpenseFilter(filters.FilterSet):
    min_date = filters.DateFilter(field_name="date", lookup_expr='gte')
    max_date = filters.DateFilter(field_name="date", lookup_expr='lte')
    min_amount = filters.NumberFilter(field_name="amount", lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name="amount", lookup_expr='lte')
    start_date = filters.DateFilter(field_name="start_date", lookup_expr='gte')
    end_date = filters.DateFilter(field_name="end_date", lookup_expr='lte')
    description = filters.CharFilter(field_name="description", lookup_expr='icontains')
    type = filters.CharFilter(field_name="type__name", lookup_expr='icontains')
    is_recurring = filters.BooleanFilter(field_name="is_recurring")

    class Meta:
        model = Expense
        fields = ['min_date', 'max_date', 'min_amount', 'max_amount','start_date', 'end_date', 'description', 'type', 'is_recurring']
