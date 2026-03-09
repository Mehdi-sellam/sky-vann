from django.db import models

# Create your models here.
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from account.models import User
from django.db.models import JSONField


class History(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField(unique=False)
    field_name = models.CharField(max_length=100)
    old_value = JSONField(null=True, blank=True)
    new_value = JSONField(null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    # GenericForeignKey to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name_plural = "History"
        indexes = [
            models.Index(fields=['user', 'table_name', 'action']),
        ]
