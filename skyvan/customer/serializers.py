from rest_framework import serializers
from .models import Customer, Contact
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from .error_codes import CustomerErrorCode
from decimal import Decimal


class CustomerSerializerFroSale(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["uuid", "name", "balance"]


class CustomerSerializerFroReturnSale(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["uuid", "name", "balance"]


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = "__all__"


class CustomerSerializerForPayment(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = ["uuid", "name", "balance_init", "balance"]


class CreateCustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    def validate_email(self, value):
        # First, perform the email format validation
        email_validator = EmailValidator(message="")
        try:
            email_validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                {
                    "code": CustomerErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email",
                }
            )
        return value

    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return value

    class Meta:
        model = Customer
        fields = ("uuid", "name", "email", "phone", "address", "balance_init")
        extra_kwargs = {
            "balance_init": {"default": Decimal("0.0")},
        }


class UpdateCustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    def validate_email(self, value):
        # First, perform the email format validation
        email_validator = EmailValidator(message="")
        try:
            email_validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                {
                    "code": CustomerErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email",
                }
            )
        return value

    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return value

    class Meta:
        model = Customer
        fields = ("uuid", "name", "email", "phone", "address", "balance_init")
        extra_kwargs = {
            "balance_init": {"required": False},  # Optional for partial updates
            "email": {"required": False},  # Optional for partial updates
            "phone": {"required": False},  # Optional for partial updates
        }


class ContactSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    def validate_email(self, value):
        # First, perform the email format validation
        email_validator = EmailValidator(message="")
        try:
            email_validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                {
                    "code": CustomerErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email",
                }
            )
        return value

    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return value

    class Meta:
        model = Contact
        fields = "__all__"
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
            "phone": {"required": True},
            "address": {"required": True},
            "customer": {"required": True},  # Set 'customer' as read-only
        }


class UpdateContactSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    def validate_email(self, value):
        # First, perform the email format validation
        email_validator = EmailValidator(message="")
        try:
            email_validator(value)
        except ValidationError:
            raise serializers.ValidationError(
                {
                    "code": CustomerErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email",
                }
            )
        return value

    email = serializers.EmailField(max_length=255)
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return value

    class Meta:
        model = Contact
        exclude = ["customer", "uuid"]


class CustomerSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = ["uuid", "name", "phone", "address"]
