from django.contrib import admin
from .models import Organisation, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days")
    ordering = ("price",)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "owner",
        "is_active",
        "created_at",
        "subscription_plan",
        "subscription_start",
        "subscription_end",
    )
    search_fields = (
        "name",
        "owner__phone",
    )  # ✅ Fix: Use `owner__phone` instead of `username`
    list_filter = ("is_active", "subscription_plan")
    ordering = ("-created_at",)
    fields = (
        "name",
        "owner",
        "is_active",
        "subscription_plan",
        "subscription_start",
        "subscription_end",
    )

    readonly_fields = ("subscription_start", "subscription_end")

    def get_readonly_fields(self, request, obj=None):
        """Ensure only `subscription_start` and `subscription_end` are readonly."""
        readonly_fields = ("subscription_start", "subscription_end")
        if obj:  # Editing existing object
            return readonly_fields + ("owner",)  # Add owner only if updating
        return readonly_fields

    def owner(self, obj):
        """Fix owner display by showing the owner's phone number."""
        return obj.owner.phone if obj.owner else "No Owner"

    owner.admin_order_field = "owner__phone"  # Allows sorting by owner
    owner.short_description = "Owner Phone"  # Renames the column in the admin panel

    def has_delete_permission(self, request, obj=None):
        """Disable delete permission (removes delete button)."""
        return False  # ✅ Prevent deletion

    def save_model(self, request, obj, form, change):
        """Automatically activate or update a subscription when a plan is assigned."""
        if obj.subscription_plan:
            if (
                not obj.subscription_start or change
            ):  # If first-time assignment or update
                obj.activate_subscription(obj.subscription_plan)  # Activate new plan
        super().save_model(request, obj, form, change)
