

from django.db import transaction
from django.utils import timezone
from history.utils import add_history_record
from dateutil.parser import isoparse
import pytz


def get_date_in_algeria_timezone(dt):
    """
    Convert a datetime (usually UTC) to Algeria timezone and return the date part.

    Args:
        dt (datetime): A timezone-aware datetime object (e.g., created_at)

    Returns:
        date: The date in Algeria time
    """
    algeria_tz = pytz.timezone("Africa/Algiers")
    local_datetime = dt.astimezone(algeria_tz)
    return local_datetime.date()


def sync_model(model_cls, payload_list, user, serializer=None):
    successes = []

    if not serializer:
        serializer = model_cls.serializer_class

    with transaction.atomic():
        for payload in payload_list:
            if 'updated_at' not in payload:
                return False, {'error': 'Missing updated_at'}

            try:
                instance = model_cls.objects.get(uuid=payload['uuid'])
            except model_cls.DoesNotExist:
                instance = None

            if instance and instance.updated_at >= isoparse(payload['updated_at']):
                continue

            old_instance = None
            if instance:
                old_instance = model_cls(
                    **{field.name: getattr(instance, field.name) for field in instance._meta.fields})

            payload['last_synced_at'] = timezone.now()
            if not instance:
                serializer_instance = serializer(data=payload)
            else:
                serializer_instance = serializer(instance, data=payload)

            if serializer_instance.is_valid():
                instance = serializer_instance.save()
                successes.append(serializer_instance.data)
                action = 'create' if not old_instance else 'update'
                print(old_instance,)
                add_history_record(user, instance, old_instance, action)
                if 'deleted' in payload and payload['deleted']:
                    if instance:
                        add_history_record(user, instance, None, 'delete')
            else:
                return False, serializer_instance.errors

    return True, {'success': f"{model_cls.__name__}s synchronized successfully", 'data': successes}
