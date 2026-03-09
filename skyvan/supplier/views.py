from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import Supplier
from .services import *
from .error_codes import SupplierErrorCode
from core.pagination import CustomPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from .filters import SupplierFilter


class SupplierListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SupplierFilter
    search_fields = ["name", "email", "phone", "address"]
    ordering_fields = ["created_at", "updated_at", "name", "email"]

    @extend_schema(
        description="Retrieve a list of suppliers with pagination, search, filtering, and ordering capabilities. Available ordering fields: created_at, updated_at, name, email.",
        responses={200: SupplierSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample("Order by name descending", value="-name"),
                    OpenApiExample("Order by email", value="email"),
                    OpenApiExample(
                        "Order by updated_at descending", value="-updated_at"
                    ),
                ],
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search query for filtering results.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="name",
                location=OpenApiParameter.QUERY,
                description="Filter results where name contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="email",
                location=OpenApiParameter.QUERY,
                description="Filter results where email contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="phone",
                location=OpenApiParameter.QUERY,
                description="Filter results where phone contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="address",
                location=OpenApiParameter.QUERY,
                description="Filter results where address contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter results where created_at is greater than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter results where created_at is less than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="updated_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter results where updated_at is greater than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="updated_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter results where updated_at is less than or equal to this value.",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, format=None):
        suppliers = self.get_queryset()
        suppliers = self.filter_queryset(request, suppliers)
        
        
        # Paginate results
        paginator = self.pagination_class()
        paginated_suppliers = paginator.paginate_queryset(suppliers, request)
        serializer = SupplierSerializer(paginated_suppliers, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Supplier.objects.none()
        return get_supplier_list()


class SupplierDetailView(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        description="Retrieve details of a supplier by UUID.",
        responses={200: SupplierSerializer},
    )
    def get(self, request, uuid, format=None):
        try:
            supplier = Supplier.objects.get(uuid=uuid, deleted=False)
        except Supplier.DoesNotExist:
            error_data = {
                "code": SupplierErrorCode.NOT_FOUND.value,
                "message": f"Supplier with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = SupplierSerializer(supplier)
        return Response(serializer.data)


class SupplierCreateView(APIView):
    @extend_schema(
        description="Create a new supplier.",
        request=CreateSupplierSerializer,
        responses={201: SupplierSerializer, 400: dict},
    )
    def post(self, request, format=None):
        serializer = CreateSupplierSerializer(data=request.data)
        if serializer.is_valid():
            try:
                supplier = create_supplier(serializer.validated_data)
                supplier_serializer = SupplierSerializer(supplier)
                return Response(
                    supplier_serializer.data, status=status.HTTP_201_CREATED
                )
            except ValidationError as e:
                return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Return validation errors if serializer is invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplierUpdateView(APIView):
    @extend_schema(
        description="Update an existing supplier by UUID.",
        request=UpdateSupplierSerializer,
        responses={200: SupplierSerializer, 400: dict, 404: dict},
    )
    def put(self, request, uuid, format=None):
        serializer = UpdateSupplierSerializer(data=request.data)
        if serializer.is_valid():
            try:
                supplier = update_supplier(uuid, serializer.validated_data)
                supplier_serializer = SupplierSerializer(supplier)
                return Response(supplier_serializer.data)
            except ValidationError as e:
                return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplierDeleteView(APIView):
    @extend_schema(
        description="Soft delete a supplier by UUID, marking it as deleted without removing it from the database.",
        responses={
            204: None,
            404: {"description": "Supplier not found"},
            400: {
                "description": "Validation error or associated records prevent deletion."
            },
        },
    )
    def delete(self, request, uuid, format=None):
        try:
            # Attempt to delete the supplier
            delete_supplier(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            # Extract validation error messages properly
            error_data = {
                "code": e.message_dict.get("code", SupplierErrorCode.NOT_FOUND.value),
                "message": e.message_dict.get("message", "Validation error"),
                "field": e.message_dict.get("field", None),
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        except Supplier.DoesNotExist:
            # Handle case where supplier does not exist
            error_data = {
                "code": SupplierErrorCode.NOT_FOUND.value,
                "message": f"Supplier with UUID {uuid} not found.",
                "field": "UUID",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
