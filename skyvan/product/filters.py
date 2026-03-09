# filters.py
import django_filters
from .models import Category

class CategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    parent = django_filters.UUIDFilter(field_name='parent__uuid')

    class Meta:
        model = Category
        fields = ['name', 'parent']



from .models import Product

class ProductFilter(django_filters.FilterSet):
    barcode = django_filters.CharFilter(field_name='barcodes__code', lookup_expr='exact')
    category_id = django_filters.NumberFilter(field_name='category__id', lookup_expr='exact')
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['barcode', 'category_id', 'category_name']