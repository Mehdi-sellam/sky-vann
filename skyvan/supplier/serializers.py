from rest_framework import serializers
from .models import Supplier
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from .error_codes import SupplierErrorCode

class SupplierSerializerFroPurchase(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["uuid","name","balance"]

class SupplierSerializerFroReturnPurchase(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["uuid","name","balance"]

class SupplierSerializerFroSupplierPayment(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["uuid","name"]
        
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
 
class SupplierSerializerForPayment(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['uuid', 'name', 'balance_init','balance']


class CreateSupplierSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        if value:
        # First, perform the email format validation
            email_validator = EmailValidator(message="")
            try:
                email_validator(value)
            except ValidationError:
                raise serializers.ValidationError({
                    "code": SupplierErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email"
                })
        return value
    def validate_phone(self, value):
        if value:
            # Add any custom phone validation logic here if needed
            pass
        return value

    class Meta:
        model = Supplier
        fields = ['uuid', 'name', 'email', 'phone', 'address','balance_init']
        extra_kwargs = {
            'uuid': {'required': True},
            'name': {'required': True},
            'address': {'required': True},
        }


class UpdateSupplierSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        if value:
        # First, perform the email format validation
            email_validator = EmailValidator(message="")
            try:
                email_validator(value)
            except ValidationError:
                raise serializers.ValidationError({
                    "code": SupplierErrorCode.INVALID.value,
                    "message": "Invalid email address format.",
                    "field": "email"
                })
        return value
    def validate_phone(self, value):
        if value:
            # Add any custom phone validation logic here if needed
            pass
        return value
 
    class Meta:
        model = Supplier
        fields = ['name', 'email', 'phone', 'address','balance_init']


class SupplierSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Supplier
        fields = ["uuid", "name", "phone", "address"]


