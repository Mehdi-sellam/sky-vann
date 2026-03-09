import django_filters
from .models import Van, VanAssignment, User, VanInventory
from .error_codes import VanErrorCode
from django.core.exceptions import ValidationError
from .enums import VanStatus


class VanAssignmentFilter(django_filters.FilterSet):
    van_uuid = django_filters.UUIDFilter(
        field_name="van__uuid", method="validate_van_uuid"
    )
    user_uuid = django_filters.UUIDFilter(
        field_name="user__uuid", method="validate_user_uuid"
    )
    is_active = django_filters.BooleanFilter(field_name="is_active")
    start = django_filters.DateTimeFromToRangeFilter(field_name="start_datetime")
    end = django_filters.DateTimeFromToRangeFilter(field_name="end_datetime")

    class Meta:
        model = VanAssignment
        fields = ["van_uuid", "user_uuid", "is_active", "start", "end"]

    def validate_van_uuid(self, queryset, name, value):
        if not Van.objects.filter(uuid=value, deleted=False).exists():
            raise ValidationError(f"Van with UUID '{value}' not found.")
        return queryset.filter(**{name: value})

    def validate_user_uuid(self, queryset, name, value):
        if not User.objects.filter(uuid=value, deleted=False).exists():
            raise ValidationError(f"User with UUID '{value}' not found.")
        return queryset.filter(**{name: value})


class VanFilter(django_filters.FilterSet):

    license_plate = django_filters.CharFilter(
        field_name="license_plate", lookup_expr="icontains"
    )
    is_working = django_filters.BooleanFilter(method="filter_is_working")
    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=VanStatus.CHOICES,
    )

    class Meta:
        model = Van
        fields = ["license_plate"]

    def filter_is_working(self, queryset, name, value):
        if value:
            # Return vans that have an active assignment
            return queryset.filter(assignments__is_active=True).distinct()
        else:
            # Return vans with NO active assignment
            return queryset.exclude(assignments__is_active=True).distinct()


class VanInventoryFilter(django_filters.FilterSet):
    class Meta:
        model = VanInventory
        fields = []
