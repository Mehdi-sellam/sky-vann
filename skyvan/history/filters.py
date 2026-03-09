from django_filters import rest_framework as filters
from .models import History


class HistoryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="timestamp", lookup_expr='gte')
    end_date = filters.DateFilter(field_name="timestamp", lookup_expr='lte')

    class Meta:
        model = History
        fields = ['user', 'table_name', 'action', 'start_date', 'end_date']
