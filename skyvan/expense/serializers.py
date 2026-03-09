from rest_framework import serializers
from .models import ExpenseType, Expense
from .error_codes import ExpenseErrorCode  # Assuming this is the correct path for ExpenseErrorCode import
from uuid import uuid4

# ExpenseType Serializer
class ExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = '__all__'
class CreateExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = ['uuid','name', 'description']

    def create(self, validated_data):
        return ExpenseType.objects.create(**validated_data)
class UpdateExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = ['name', 'description']
class TypeForExpenseListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = ['uuid','name','description']
class TypeForBudgetListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = ['uuid','name','description']


# Expense Serializer
class ExpenseSerializer(serializers.ModelSerializer):
    type = TypeForExpenseListingSerializer()
    class Meta:
        model = Expense
        fields = '__all__'
class CreateExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['uuid', 'description', 'type','amount', 'date', 'is_recurring', ] 

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError({
                "code": ExpenseErrorCode.AMOUNT_INVALID.value,
                "message": "Amount must be greater than zero.",
                "field": "amount"
            })
        return value

    def create(self, validated_data):
        return Expense.objects.create(**validated_data)
class UpdateExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        exclude = ['uuid']


class ExpenseListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['uuid','description', 'type','amount', 'date', 'is_recurring',]





