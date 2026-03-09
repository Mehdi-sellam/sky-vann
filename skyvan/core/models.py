from django.db import models
from django.conf import settings
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True



class UserAuthorModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_updated",
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_by"]),
        ]