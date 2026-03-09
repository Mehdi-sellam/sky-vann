from django.forms import ValidationError
from drf_spectacular.types import OpenApiTypes
from rest_framework.response import Response
from rest_framework import status
from .services import *
from .models import SaleOrder
from rest_framework.views import APIView
from .error_codes import SaleOrderErrorCode
from .serializers import *
from core.pagination import CustomPagination, ReportPagination
from .filters import SaleOrderFilter, SaleLineReportFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.db.models import Sum, F, DecimalField
from rest_framework.permissions import IsAuthenticated


class SaleOrderListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SaleOrderFilter
    search_fields = ["customer__name", "warehouse__name", "lines__product__name"]
    ordering_fields = ["created_at", "total_price", "customer__name", "number", "date", "created_by__full_name", "updated_by__full_name"]

    @extend_schema(
        responses={200: SaleOrderSerializer(many=True)},
        description="Retrieve a list of sale orders with pagination, search, filtering, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by customer name or warehouse.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description='''Order by fields like `created_at`, `total_price`, 'created_by__full_name', 'updated_by__full_name' 
                (add or remove '-' for reverse ordering)''',
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),
                ],
            ),
        ],
        tags=["sales_orders"],
    )
    def get(self, request):
        orders = self.get_queryset()
        orders = self.filter_queryset(request, orders)

        # Paginate results
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)
        serializer = SaleOrderSerializer(paginated_orders, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        """
        Apply filter, search, and ordering using backends.
        """
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SaleOrder.objects.none()
        return get_all_sale_orders()


class SaleOrderDetailView(APIView):
    @extend_schema(
        responses={200: SaleOrderSerializer},
        description="Retrieve details of a specific sale order.",
        tags=["sales_orders"],
    )
    def get(self, request, uuid):
        try:
            sale_order = get_sale_order_by_uuid(uuid)
            serializer = SaleOrderSerializer(sale_order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(
                {"code": "unknown_error", "message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaleOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CreateSaleOrderSerializer,
        responses={201: SaleOrderSerializer},
        description="Create a new sale order.",
        tags=["sales_orders"],
    )
    def post(self, request):
        serializer = CreateSaleOrderSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale_order = create_sale_order(request.user, serializer.validated_data)
            response_serializer = SaleOrderSerializer(sale_order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "Error", "message": f"{e}", "field": "???"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaleOrderUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=UpdateSaleOrderSerializer,
        responses={200: SaleOrderSerializer},
        description="Update a specific sale order.",
        tags=["sales_orders"],
    )
    def put(self, request, uuid):
        try:
            sale_order = get_sale_order_by_uuid(uuid)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateSaleOrderSerializer(data=request.data)

        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        try:
            updated_order = update_sale_order(request.user, sale_order, validated_data)
            response_serializer = SaleOrderSerializer(updated_order)
            return Response(response_serializer.data)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": "UNKNOWN_ERROR",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "UUID",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaleOrderDeleteView(APIView):
    @extend_schema(
        responses={204: None},
        description="Soft delete a specific sale order.",
        tags=["sales_orders"],
    )
    def delete(self, request, uuid):
        try:
            delete_sale_order(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)  # Success
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except APIException as e:
            return Response(e.detail, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(
                {
                    "code": "UNKNOWN_ERROR",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "UUID",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaleOrderLinesView(APIView):
    @extend_schema(
        responses={200: SaleLineSerializer(many=True)},
        description="Retrieve a list of lines for a specific sale order.",
        tags=["sales_orders"],
        parameters=[
            OpenApiParameter(
                name="page",
                location=OpenApiParameter.QUERY,
                description="Page number for pagination.",
                required=False,
                type=int,
                examples=[OpenApiExample("Page 2", value=2)],
            ),
            OpenApiParameter(
                name="page_size",
                location=OpenApiParameter.QUERY,
                description="Number of results per page.",
                required=False,
                type=int,
                examples=[OpenApiExample("20 results per page", value=20)],
            ),
        ],
    )
    def get(self, request, uuid):
        try:
            sale_lines = get_sale_order_lines(uuid)
            serializer = SaleLineSerializer(sale_lines, many=True)
            return Response(serializer.data)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": "UNKNOWN_ERROR",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "UUID",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SaleLineReportView(APIView):
    pagination_class = ReportPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SaleLineReportFilter
    search_fields = ["sale_order__customer__name", "product__name"]
    ordering_fields = [
        "created_at",
        "sale_order__date",
        "product__name",
        "total_price",
        "quantity",
        "unit_price",
        "sale_order__warehouse__name",
        "sale_order__customer__name",  # Order by Customer Name
        "sale_order__number",
    ]

    @extend_schema(
        responses={200: SaleLineReportSerializer()},
        description="Retrieve a list of sale lines with pagination, search, filtering, ordering, and total calculations.",
        parameters=[
            OpenApiParameter(
                name="page",
                location=OpenApiParameter.QUERY,
                description="Page number for pagination.",
                required=False,
                type=int,
                examples=[OpenApiExample("Page 2", value=2)],
            ),
            OpenApiParameter(
                name="page_size",
                location=OpenApiParameter.QUERY,
                description="Number of results per page.",
                required=False,
                type=int,
                examples=[OpenApiExample("20 results per page", value=20)],
            ),
            OpenApiParameter(
                name="customer_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by customer UUID.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Filter by a specific customer",
                        value="123e4567-e89b-12d3-a456-426614174000",
                    )
                ],
            ),
            OpenApiParameter(
                name="product_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by product UUID.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Filter by a specific product",
                        value="789e1234-e56b-78c9-a012-345678901234",
                    )
                ],
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by customer name or product name.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order by fields like `created_at`, `total_price`, `quantity`, `customer_name`, or `sale_number`.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="date"),
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample(
                        "Order by customer name", value="sale_order__customer__name"
                    ),
                    OpenApiExample(
                        "Order by sale number descending", value="-sale_order__number"
                    ),
                    OpenApiExample("Order by quantity descending", value="-quantity"),
                    OpenApiExample("Order by quantity", value="quantity"),
                ],
            ),
            OpenApiParameter(
                name="date_after",
                location=OpenApiParameter.QUERY,
                description="Filter by sale order creation date (after this date).",
                required=False,
                type=str,
                examples=[OpenApiExample("After January 1, 2024", value="2024-01-01")],
            ),
            OpenApiParameter(
                name="date_before",
                location=OpenApiParameter.QUERY,
                description="Filter by sale order creation date (before this date).",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Before January 31, 2024", value="2024-01-31")
                ],
            ),
        ],
        tags=["sale_lines_report"],
    )
    def get(self, request):
        lines = self.get_queryset(request)

        try:
            lines = self.filter_queryset(request, lines)
        except ValidationError as e:
            return self.handle_validation_error(e)

        # Compute totals before pagination
        totals = lines.aggregate(
            total_quantity=Sum(
                "quantity", output_field=DecimalField(max_digits=10, decimal_places=2)
            )
            or Decimal("0.00"),
            total_price=Sum(
                "total_price",
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
            or Decimal("0.00"),
        )

        # Paginate results
        paginator = self.pagination_class()
        paginated_lines = paginator.paginate_queryset(lines, request)
        serialized_lines = SaleLineReportDetailedSerializer(paginated_lines, many=True)

        # Return response using SaleLinePagination
        return paginator.get_paginated_response(
            serialized_lines.data,
            total_quantity=totals["total_quantity"],
            total_price=totals["total_price"],
        )

    def filter_queryset(self, request, queryset):
        """
        Apply filter, search, and ordering using backends.
        """
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def handle_validation_error(self, exception):
        """Format validation errors in the required structure"""
        # Extract the first error dictionary from ValidationError
        error_dict = exception.args[0] if isinstance(exception, ValidationError) else {}

        return Response(error_dict, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self, request):
        if getattr(self, "swagger_fake_view", False):
            return SaleLine.objects.none()
        return get_sale_line_report(request)


# sale van
class VanSaleOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CreateVanSaleOrderSerializer,
        responses={201: SaleOrderSerializer},
        description="Create a new sale order.",
        tags=["sales_orders"],
    )
    def post(self, request):
        serializer = CreateVanSaleOrderSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        try:
            sale_order = create_sale_order_from_van(request.user, serializer.validated_data)
            response_serializer = SaleOrderSerializer(sale_order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "Error", "message": f"{e}", "field": "???"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanSaleOrderUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UpdateVanSaleOrderSerializer,
        responses={200: SaleOrderSerializer},
        description="Update a specific van sale order.",
        tags=["sales_orders"],
    )
    def put(self, request, uuid):
        try:
            sale_order = get_sale_order_by_uuid(uuid)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateVanSaleOrderSerializer(data=request.data)

        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": SaleOrderErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        try:
            updated_order = update_sale_order_from_van(request.user, sale_order, validated_data)
            response_serializer = SaleOrderSerializer(updated_order)
            return Response(response_serializer.data)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": "UNKNOWN_ERROR",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "UUID",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanSaleOrderDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None},
        description="Soft delete a specific sale order.",
        tags=["sales_orders"],
    )
    def delete(self, request, uuid):
        try:
            delete_sale_order_from_van(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)  # Success
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except APIException as e:
            return Response(e.detail, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(
                {
                    "code": "UNKNOWN_ERROR",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "UUID",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MySaleOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SaleOrderFilter
    search_fields = ["customer__name", "warehouse__name", "lines__product__name"]
    ordering_fields = ["created_at", "total_price", "customer__name", "number", "date", "created_by__full_name", "updated_by__full_name"]
       # to do  add order by user fullnames for sales and return sales

    @extend_schema(
        responses={200: MySaleOrderSerializer(many=True)},
        description="Retrieve a list of sale orders with pagination, search, filtering, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by customer name or warehouse.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description='''Order by fields like `created_at`, `total_price`, 'created_by__full_name', 'updated_by__full_name' 
                (add or remove '-' for reverse ordering)''',
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample("Order by created_by ASC", value="created_by__full_name"),
                    OpenApiExample("Order by created_by DESC", value="-created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC", value="updated_by__full_name"),
                    OpenApiExample("Order by updated_by DESC", value="-updated_by__full_name"),
                ],
            ),
             OpenApiParameter(
                name='created_by', 
                description='Filter by the UUID of the user who created the record', 
                required=False, 
                type=OpenApiTypes.UUID
            ),
            OpenApiParameter(
                name='updated_by', 
                description='Filter by the UUID of the user who last updated the record', 
                required=False, 
                type=OpenApiTypes.UUID
            ),
            OpenApiParameter(
                name='van', 
                description='Filter by the UUID of the van associated with the sale order', 
                required=False, 
                type=OpenApiTypes.UUID
            ),
        ],
        tags=["sales_orders"],
    )
    def get(self, request):
        orders = self.get_queryset()
        orders = self.filter_queryset(request, orders)

        # Paginate results
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)
        serializer = MySaleOrderSerializer(paginated_orders, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        """
        Apply filter, search, and ordering using backends.
        """
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SaleOrder.objects.none()
        return get_my_sale_orders(self.request)
