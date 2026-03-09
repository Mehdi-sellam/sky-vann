from rest_framework import serializers
from .models import Product, Barcode, Category

class BarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barcode
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class CreateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields =   ['uuid','name','parent','description']

class CategoryForProductListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['uuid','name']

class UpdateCategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255)
    def validate_name(self, value):
        return value
    class Meta:
        model = Category
        fields =   ['name','parent','description']

class UpdateProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(max_length=255)
    def validate_sku(self, value):
        return value
    class Meta:
        model = Product
        exclude = ['uuid']

class CreateProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(max_length=255)
    def validate_sku(self, value):
        return value
    class Meta:
        model = Product
        fields = '__all__'

class ProductSerializerForLines(serializers.ModelSerializer):
    category =CategoryForProductListingSerializer()
    class Meta:
        model = Product
        fields = ['uuid',"name","sku","product_type","category","price","cost_price"]

class ProductSerializerForWarehouse(serializers.ModelSerializer):
    category =CategoryForProductListingSerializer()
    class Meta:
        model = Product
        fields = ['uuid',"name","sku","product_type","category"]

class ProductSerializerForInventory(serializers.ModelSerializer):
    category =CategoryForProductListingSerializer()
    class Meta:
        model = Product
        fields = '__all__'

class ProductSerializerCustom(serializers.ModelSerializer):
    category =CategoryForProductListingSerializer()
    class Meta:
        model = Product
        fields = ['uuid', "name", "sku", "product_type","category", "price", "cost_price"]

class ProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(max_length=255)
    category =CategoryForProductListingSerializer()

    def validate_sku(self, value):
        return value
    class Meta:
        model = Product
        fields = '__all__'
