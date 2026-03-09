from rest_framework import serializers
from .models import History


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = History
        fields = ['user', 'table_name', 'record_id', 'field_name',
                  'old_value', 'new_value', 'action', 'timestamp']
