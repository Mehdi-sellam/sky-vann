import django_filters
from .models import User


class OrganizationUserFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = User
        fields = [
            "is_active",
        ]
