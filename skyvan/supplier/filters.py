import django_filters
from .models import Supplier

class SupplierFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    email = django_filters.CharFilter(field_name='email', lookup_expr='icontains')
    phone = django_filters.CharFilter(field_name='phone', lookup_expr='icontains')
    address = django_filters.CharFilter(field_name='address', lookup_expr='icontains')
    created_at_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_at_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    updated_at_after = django_filters.DateFilter(field_name='updated_at', lookup_expr='gte')
    updated_at_before = django_filters.DateFilter(field_name='updated_at', lookup_expr='lte')

    class Meta:
        model = Supplier
        fields = ['name', 'email', 'phone', 'address', 'created_at_after', 'created_at_before', 'updated_at_after', 'updated_at_before']
