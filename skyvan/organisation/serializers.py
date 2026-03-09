from .models import Organisation
from rest_framework import serializers


class OrganisationSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()

    class Meta:
        model = Organisation
        fields = ["id", "name", "owner", "created_at", "is_active"]


class OrganisationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ["name", "owner", "is_active"]


class OrganisationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ["name", "is_active"]
