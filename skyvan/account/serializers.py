from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
 
from .models import User, UserRoles
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .error_codes import UserErrorCode
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
 
class CustomLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)


    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        if not phone or not password:
            raise serializers.ValidationError(
                {
                    "code": UserErrorCode.REQUIRED.value,
                    "message": 'Must include "phone" and "password".',
                    "field": "phone" if not phone else "password",
                }
            )
        user = authenticate(
            request=self.context.get("request"), username=phone, password=password
        )

        if not user:
            raise ValidationError(
                {
                    "code": UserErrorCode.INVALID_CREDENTIALS.value,
                    "message": "Invalid credentials. Please check your phone and password.",
                    "field": "phone",
                }
            )

        if user.deleted == True:
            raise ValidationError(
                {
                    "code": UserErrorCode.INVALID_CREDENTIALS.value,
                    "message": "Invalid credentials. Please check your phone and password.",
                    "field": "phone",
                }
            )
        if not user.is_active:
            raise ValidationError(
                {
                    "code": UserErrorCode.ACCOUNT_INACTIVE.value,
                    "message": "This account is inactive. Please contact support.",
                    "field": "phone",
                }
            )
        attrs["user"] = user
        print (f"attrs : {attrs}") 
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "uuid": str(user.uuid),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
                "is_active": user.is_active,
                "role": user.role,
                "organization": user.organization if user.organization else None,
                "has_van": user.has_van,

            },
        }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Customize JWT token payload to include `organisation_id`"""

    def get_token(cls, user):
        """Customize the token payload to include `organisation_id`"""
        token = super().get_token(user)

        # ✅ Use `getattr()` to avoid importing `Organisation`
        organisation_id = getattr(user, "organisation", None)
        token["organisation_id"] = (
            organisation_id.id if organisation_id else None
        )  # ✅ Safe check

        return token

class UserAuthorSerializer(serializers.ModelSerializer):
    """Serializer for listing organization users."""


    class Meta:
        model = User
        fields = [
            "uuid",
            "phone",
            "email",
            "role",
            "first_name",
            "last_name"
        ]


class UserAuthorBaseSerializer(serializers.ModelSerializer):
    created_by = UserAuthorSerializer(read_only=True)
    updated_by = UserAuthorSerializer(read_only=True)

    class Meta:
        abstract = True


class OrganizationUserSerializer(serializers.ModelSerializer):
    """Serializer for listing organization users."""

    has_van = serializers.BooleanField(read_only=True)
    class Meta:
        model = User
        fields = [
            "uuid",
            "phone",
            "email",
            "role",
            "first_name",
            "last_name",
            "is_active",
            "has_van" 
        ]


class OrganizationUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an organization user."""

    class Meta:
        model = User
        fields = [
            "uuid",
            "phone",
            "first_name",
            "last_name",
            "email",
            "password",
        ]
        extra_kwargs = {
            "uuid": {"required": True},
            "phone": {"required": True},
            "password": {"write_only": True, "required": True},
        }


class OrganizationUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an organization user."""

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "email", "is_active", "password"]
        extra_kwargs = {
            "phone": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "email": {"required": False},
            "is_active": {"required": False},
            "password": {"write_only": True, "required": False},
        }
        
class UserLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = OrganizationUserSerializer() 
    
    
class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        return {
            'access': data.get('access'),
            'refresh': attrs.get('refresh')
        }
        
        
class  OrganizationMeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an  user."""

    class Meta:
        model = User
        fields = ["phone", "first_name", "last_name", "email", "password"]
        extra_kwargs = {
            "phone": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "email": {"required": False},
            "password": {"write_only": True, "required": False},
        }


