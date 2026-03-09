from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import get_categories_list, get_product_list
from .models import Category, Product
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.utils import sync_model
from .error_codes import *
from core.pagination import CustomPagination
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)
from .filters import CategoryFilter, ProductFilter

# class CategoryList(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, format=None):
#         last_sync_time = request.query_params.get('last_sync_time')
#         if last_sync_time:
#             categories = Category.objects.filter(
#                 last_synced_at__gt=last_sync_time)
#         else:
#             categories = Category.objects.all()
#         serializer = CategorySerializer(categories, many=True)
#         return Response(serializer.data)


class CategoryList(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [        
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,]
    filterset_class = CategoryFilter
    ordering_fields = ["name", "parent__name"]
    search_fields = ["name", "description"]

    @extend_schema(
        responses={200: CategorySerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by category name or description.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Example 1", value="name"),
                    OpenApiExample("Example 2", value="-parent__name"),
                ],
            ),
            OpenApiParameter(
                name="parent",
                location=OpenApiParameter.QUERY,
                description="Filter by parent category UUID.",
                required=False,
                type=str,
            ),
        ],
        description="Retrieve a list of categories with pagination, search, filtering, and ordering capabilities.",
    )
    
    def get(self, request, format=None):
        categories = self.get_queryset()
        categories = self.filter_queryset(request, categories)

        # Paginate results
        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Category.objects.none()
        return get_categories_list()


class CategoryDetail(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        responses={200: CategorySerializer, 404: dict},
        description="Retrieve a specific category by its UUID.",
    )
    def get(self, request, uuid, format=None):
        try:
            category = Category.objects.get(uuid=uuid, deleted=False)
        except Category.DoesNotExist:
            error_data = {
                "code": CategoryErrorCode.NOT_FOUND.value,
                "message": f"Category with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = CategorySerializer(category)
        return Response(serializer.data)


class CategoryCreate(APIView):

    @extend_schema(
        request=CreateCategorySerializer,
        responses={201: CategorySerializer, 400: dict, 404: dict},
        description="Create a new category.",
    )
    def post(self, request, format=None):
        data = request.data
        serializer = CreateCategorySerializer(data=data)
        if serializer.is_valid():
            name = serializer.validated_data.get("name")
            try:
                # Fetch the customer object based on the 'customer_uuid'
                c = Category.objects.get(name=name)
                error_data = {
                    "code": CategoryErrorCode.ALREADY_EXISTS.value,
                    "message": "Category with this name  already exists.",
                    "field": "name",
                }
                return Response(error_data, status=status.HTTP_404_NOT_FOUND)

            except Category.DoesNotExist:
                pass
            instance = serializer.save()
            response_serializer = CategorySerializer(instance)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        if first_field:
            error_data = {
                "code": CategoryErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class CategoryDelete(APIView):
    @extend_schema(
        responses={204: None, 404: dict},
        description="Delete a specific category by its UUID.",
    )
    def delete(self, request, uuid, format=None):
        try:
            category = Category.objects.get(uuid=uuid, deleted=False)
        except Category.DoesNotExist:
            error_data = {
                "code": CategoryErrorCode.NOT_FOUND.value,
                "message": f"Category with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        category.deleted = True
        category.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryUpdate(APIView):
    @extend_schema(
        request=UpdateCategorySerializer,
        responses={200: CategorySerializer, 400: dict, 404: dict},
        description="Update an existing category.",
    )
    def put(self, request, uuid, format=None):
        try:
            category = Category.objects.get(uuid=uuid, deleted=False)
        except Category.DoesNotExist:
            error_data = {
                "code": CategoryErrorCode.NOT_FOUND.value,
                "message": f"Category with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateCategorySerializer(category, data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get("name")
            existing_category = (
                Category.objects.filter(name=name)
                .exclude(uuid=category.uuid if category else None)
                .first()
            )
            if existing_category:
                error_data = {
                    "code": CategoryErrorCode.ALREADY_EXISTS.value,
                    "message": "Category with this name  already exists.",
                    "field": "name",
                }
                return Response(error_data, status=status.HTTP_404_NOT_FOUND)

            instance = serializer.save()
            response_serializer = CategorySerializer(instance)
            return Response(response_serializer.data)
        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        if first_field:
            error_data = {
                "code": CategoryErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class SyncCategory(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        categories_payload = request.data
        user = request.user

        success, data = sync_model(
            Category, categories_payload, user, serializer=CategorySerializer
        )
        if success:
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)


class ProductList(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    pagination_class = CustomPagination
    filterset_class = ProductFilter
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "price", "category__name", "product_type"]

    @extend_schema(
        responses={200: ProductSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="barcode",
                location=OpenApiParameter.QUERY,
                description="Filter by barcode",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="category_id",
                location=OpenApiParameter.QUERY,
                description="Filter by category ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="category_name",
                location=OpenApiParameter.QUERY,
                description="Filter by category name",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by product name or SKU.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("name", value="name"),
                    OpenApiExample("price", value="-price"),
                    OpenApiExample("category__name", value="-category__name"),
                    OpenApiExample("product_type", value="-product_type"),
                ],
            ),
        ],
    )
    def get(self, request, format=None):
        products = self.get_queryset()
        products = self.filter_queryset(request, products)

        # Paginate results
        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        return get_product_list()

class ProductDetail(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        responses={200: ProductSerializer, 404: dict},
        description="Retrieve a single product by UUID.",
    )
    def get(self, request, uuid, format=None):
        try:
            product = Product.objects.get(uuid=uuid, deleted=False)
        except Product.DoesNotExist:
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": f"Product with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class ProductCreate(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        request=CreateProductSerializer,
        responses={201: ProductSerializer, 400: dict},
        description="Create a new product.",
    )
    def post(self, request, format=None):
        serializer = CreateProductSerializer(data=request.data)
        if serializer.is_valid():
            sku = serializer.validated_data.get("sku")
            try:
                # Check if a product with the same SKU already exists
                existing_product = Product.objects.get(sku=sku)
                error_data = {
                    "code": ProductErrorCode.ALREADY_EXISTS.value,
                    "message": "Product with this SKU already exists.",
                    "field": "sku",
                }
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
            except Product.DoesNotExist:
                pass

            serializer.validated_data["average_cost"] = serializer.validated_data[
                "cost_price"
            ]
            product = serializer.save()
            serializer = ProductSerializer(product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        if first_field:

            message = str(first_errors) if first_errors else "Unknown error"
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class ProductDelete(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        responses={204: None, 404: dict}, description="Delete a product by UUID."
    )
    def delete(self, request, uuid, format=None):
        try:
            product = Product.objects.get(uuid=uuid, deleted=False)
        except Product.DoesNotExist:
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": f"Product with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        # Check if the product has related transactions
        has_sales = product.sale_lines.filer(deleted=False).exists()
        has_purchases = product.purchase_lines.filer(deleted=False).exists()
        has_sale_returns = product.return_sale_lines.filer(deleted=False).exists()
        has_purchase_returns = product.return_purchase_lines.filer(deleted=False).exists()
        if has_sales or has_purchases or has_sale_returns or has_purchase_returns:
            error_data = {
                "code": ProductErrorCode.CANNOT_DELETE.value,
                "message": "Cannot delete product. It has associated sales, purchases, or returns.",
                "field": "UUID",
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        
        product.deleted = True
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductUpdate(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        request=UpdateProductSerializer,
        responses={200: ProductSerializer, 400: dict, 404: dict},
        description="Update an existing product by UUID.",
    )
    def put(self, request, uuid, format=None):
        try:
            product = Product.objects.get(uuid=uuid)
        except Product.DoesNotExist:
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": f"Product with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateProductSerializer(product, data=request.data)
        if serializer.is_valid():
            sku = serializer.validated_data.get("sku")
            # Check if updating to a SKU that already exists
            if sku != product.sku and Product.objects.filter(sku=sku).exists():
                error_data = {
                    "code": ProductErrorCode.ALREADY_EXISTS.value,
                    "message": "Product with this SKU already exists.",
                    "field": "sku",
                }
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

            product = serializer.save()
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        if first_field:
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class SyncProduct(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer  # ✅ Add this

    @extend_schema(
        request=ProductSerializer(many=True),
        responses={201: ProductSerializer(many=True), 400: ""},  # Optional
        description="Sync list of product objects to the backend.",
    )
    def post(self, request, format=None):
        products_payload = request.data
        user = request.user

        success, data = sync_model(
            Product, products_payload, user, serializer=ProductSerializer
        )
        if success:
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(data, status=status.HTTP_400_BAD_REQUEST)


class ProductBarcodeUpdate(APIView):
    pagination_class = CustomPagination

    @extend_schema(
        request=inline_serializer(
            name="ProductBarcodeUpdateRequest",
            fields={
                "removed_barcode_ids": serializers.ListField(
                    child=serializers.IntegerField(), required=False
                ),
                "added_barcodes": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
                "updated_barcodes": serializers.ListField(
                    child=inline_serializer(
                        name="UpdatedBarcode",
                        fields={
                            "id": serializers.IntegerField(),
                            "code": serializers.CharField(),
                        },
                    ),
                    required=False,
                ),
            },
        ),
        responses={
            200: BarcodeSerializer(many=True),
            400: inline_serializer(
                name="ErrorResponse400",
                fields={
                    "code": serializers.CharField(),
                    "message": serializers.CharField(),
                    "field": serializers.CharField(),
                },
            ),
            404: inline_serializer(
                name="ErrorResponse404",
                fields={
                    "code": serializers.CharField(),
                    "message": serializers.CharField(),
                    "field": serializers.CharField(),
                },
            ),
        },
        description="Update barcodes for a product. You can add, remove, or update barcodes.",
    )
    def post(self, request, uuid, format=None):
        with transaction.atomic():
            try:
                product = Product.objects.get(uuid=uuid, deleted=False)
            except Product.DoesNotExist:
                error_data = {
                    "code": ProductErrorCode.NOT_FOUND.value,
                    "message": f"Product with UUID {uuid} not found.",
                    "field": "UUID.",
                }
                return Response(error_data, status=status.HTTP_404_NOT_FOUND)

                # Deserialize the request data using BarcodeSerializer
            removed_barcode_ids = request.data.get("removed_barcode_ids", [])
            if removed_barcode_ids:
                Barcode.objects.filter(
                    id__in=removed_barcode_ids, product=product
                ).delete()

            added_barcode_data = request.data.get("added_barcodes", [])
            if added_barcode_data:
                for barcode_data in added_barcode_data:
                    try:
                        b = Barcode.objects.get(code=barcode_data, product=product)
                        if b:
                            error_data = {
                                "code": ProductErrorCode.ALREADY_EXISTS.value,
                                "message": f"barcode  {barcode_data} already exists.",
                                "field": "code.",
                            }
                            return Response(
                                error_data, status=status.HTTP_404_NOT_FOUND
                            )

                    except Barcode.DoesNotExist:

                        barcode = Barcode(product=product, code=barcode_data)
                        barcode.save()

            updated_barcode_data = request.data.get("updated_barcodes", [])
            if updated_barcode_data:
                for barcode_data in updated_barcode_data:
                    barcode_id = barcode_data["id"]
                    try:
                        barcode = Barcode.objects.get(id=barcode_id, product=product)
                    except Product.DoesNotExist:
                        error_data = {
                            "code": ProductErrorCode.NOT_FOUND.value,
                            "message": f"barcode  code:{barcode_data} not found.",
                            "field": "code.",
                        }
                        return Response(error_data, status=status.HTTP_404_NOT_FOUND)

                    barcode.code = barcode_data["code"]
                    barcode.save()

            barcodes = Barcode.objects.filter(product=product)

            paginator = self.pagination_class()
            paginated_barcodes = paginator.paginate_queryset(barcodes, request)

            serializer = BarcodeSerializer(paginated_barcodes, many=True)
            return paginator.get_paginated_response(serializer.data)


class ProductBarcodeListView(APIView):
    pagination_class = CustomPagination

    @extend_schema(
        responses={
            200: BarcodeSerializer(many=True),
            404: dict,
        },
        description="Retrieve a list of barcodes for a product.",
    )
    def get(self, request, uuid, format=None):
        try:
            product = Product.objects.get(uuid=uuid, deleted=False)
            barcodes = Barcode.objects.filter(product=product)

            paginator = self.pagination_class()
            paginated_barcodes = paginator.paginate_queryset(barcodes, request)

            serializer = BarcodeSerializer(paginated_barcodes, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Product.DoesNotExist:
            error_data = {
                "code": ProductErrorCode.NOT_FOUND.value,
                "message": f"Product with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
