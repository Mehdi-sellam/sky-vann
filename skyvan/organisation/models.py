from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta


class SubscriptionPlan(models.Model):
    """Represents different subscription plans."""

    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)  # Default subscription is 30 days

    def __str__(self):
        return f"{self.name} - {self.price} DZD ({self.duration_days} days)"


class Organisation(models.Model):
    """Represents an organisation using the SaaS platform."""

    name = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    owner = models.OneToOneField(
        "account.User",
        on_delete=models.CASCADE,
        related_name="organisation",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Subscription Fields
    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True
    )
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    phone_numbers = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        help_text="Enter up to 4 phone numbers separated by commas.",
    )
    # logo = models.ImageField(upload_to="organisation_logos/", null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    invoice_footer_message = models.TextField(null=True, blank=True)
    show_invoice_footer = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """Prevent deletion of Organisation objects."""
        raise ValidationError("Deletion of organisations is not allowed.")

    def activate_subscription(self, plan):
        """Activates a subscription for the organisation."""
        self.subscription_plan = plan
        self.subscription_start = now()
        self.subscription_end = now() + timedelta(days=plan.duration_days)
        self.is_active = True
        self.save()

    def check_subscription_status(self):
        """Checks if the subscription is still active."""
        if self.subscription_end and self.subscription_end < now():
            self.is_active = False  # Expired subscription
            self.save()

    def renew_subscription(self):
        """Renews subscription by extending the end date."""
        if self.subscription_plan:
            self.subscription_end = now() + timedelta(
                days=self.subscription_plan.duration_days
            )
            self.is_active = True
            self.save()
