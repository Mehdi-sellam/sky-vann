from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import History
from typing import Any, Dict
from django.db.models import Model
from datetime import datetime


# def instance_to_dict(instance: Model) -> Dict[str, Any]:
#     fields = instance._meta.fields
#     field_names = [f.name for f in fields]
#     return {name: getattr(instance, name) if name != 'uuid' and not isinstance(getattr(instance, name), datetime) else str(getattr(instance, name)) for name in field_names}
import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def instance_to_dict(instance: Model) -> Dict[str, Any]:
    fields = instance._meta.fields
    field_names = [f.name for f in fields]
    data = {}
    for name in field_names:
        value = getattr(instance, name)
        if name != 'uuid' and not isinstance(value, datetime):
            if isinstance(value, Decimal):
                data[name] = str(value)
            else:
                data[name] = value
    return data
def add_history_record(user, instance, old_instance,action):
    content_type = ContentType.objects.get_for_model(instance.__class__)
    print(instance.uuid)
    old_values = {}
    new_values = {}
    if action == 'create':
        new_values = instance_to_dict(instance)

    elif action == 'update':
        for field in instance._meta.fields:
            field_name = field.name


            old_value = str(getattr(old_instance, field_name))
            new_value = str(getattr(instance, field_name))
  
            if old_value != new_value:
                old_values[field_name] = old_value
                new_values[field_name] = new_value

    elif action == 'delete':
        old_values = instance_to_dict(instance)
    else:
        return None

    history_record = History(
        user=user,
        table_name=instance.__class__.__name__,
        record_id=instance.pk,
        field_name='all' if action == 'create' else ','.join(
            new_values.keys()),
        old_value=old_values,
        new_value=new_values,
        action=action,
        timestamp=timezone.now(),
        content_type=content_type,
        object_id=instance.pk,
    )
    history_record.save()
