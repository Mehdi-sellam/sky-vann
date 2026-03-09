from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    """Customize Django Admin for User model."""

    list_display = (
        "id",
        "phone",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "is_active",
    )
    search_fields = ("phone", "first_name", "last_name", "email")
    ordering = ("phone",)
    list_filter = ("is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    # ✅ Remove references to `groups` and `user_permissions`
    filter_horizontal = ()  # ✅ Fix the error

    def get_fieldsets(self, request, obj=None):
        """Prevent editing the phone field after creation."""
        if obj:
            return (
                (None, {"fields": ("phone", "password")}),
                ("Personal Info", {"fields": ("first_name", "last_name", "email")}),
                ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
            )
        return super().get_fieldsets(request, obj)


admin.site.register(User, UserAdmin)
