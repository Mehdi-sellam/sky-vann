
from rest_framework import serializers
from decimal import Decimal
from django.conf import settings
from product.models import Barcode, Product
from account.serializers import UserAuthorSerializer
from van.models import VanAssignment
from van.serializers import VanSerializerMinInfo


class ProfitStatisticsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    cogs = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    cogs_value_average_cost = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )  # Uses  purchase average cost
    total_expenses = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    gross_profit = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    net_profit = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    profit_margin = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    client_balances = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    supplier_balances = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )
    inventory_value_cost = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )  # Uses average cost
    inventory_value_average_cost = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )  # Uses  purchase average cost
    total_purchases = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
    )

    def to_representation(self, instance):
        """Ensure all numbers are returned as strings with two decimal places."""
        data = super().to_representation(instance)
        for key in data:
            data[key] = f"{Decimal(data[key]):.2f}"  # Convert to string with 2 decimals
        return data


class CategoryForProductSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()

class BarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barcode
        fields = '__all__'

class ProductDetailsSerializer(serializers.ModelSerializer):
    """Handles the nested product information"""
    category = CategoryForProductSerializer(read_only=True)
    barcodes = BarcodeSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            'uuid',
            'name', 
            'sku', 
            'product_type', 
            'category', 
            'price', 
            'cost_price',
            'barcodes',
        ]

class ProductStatisticsSerializer(serializers.Serializer):
    """The response structure for calculating all-time products statistics"""
    
    product = ProductDetailsSerializer(source='*')
    
    opening_quantity = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )
    quantity_transfered_warehouse_to_van = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )
    quantity_transfered_van_to_warehouse = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )
    quantity_sold = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )
    quantity_returned_sale = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )
    remaining_quantity = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS, 
        decimal_places=settings.DEFAULT_DECIMAL_PLACES
    )


class MostSoldProductsSerializer(serializers.Serializer):
    product = ProductDetailsSerializer(source="*")
    quantity_sold = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )


class SortedExpectedRevenueSerializer(serializers.Serializer):
    product = ProductDetailsSerializer(source="*")
    quantity_sold = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    avg_unit_price = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    net_revenue = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )



#class SortedNetProfitSerializer(serializers.Serializer):
#    product = ProductDetailsSerializer(source="*")
#    profit = serializers.DecimalField(
#        max_digits=settings.DEFAULT_MAX_DIGITS,
#        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
#        read_only=True,
#    )


class SortedNetProfitSerializer(serializers.Serializer):
    product = ProductDetailsSerializer(source="*")
    quantity_sold = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    avg_unit_cost_price = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    total_cost_value = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    net_revenue = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )
    profit = serializers.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        read_only=True,
    )