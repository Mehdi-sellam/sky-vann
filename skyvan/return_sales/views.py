from decimal import Decimal
from rest_framework.exceptions import ValidationError

from django.db.models import Sum, DecimalField
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters

from .filters import ReturnSaleOrderFilter, ReturnSaleLineReportFilter
from .models import ReturnSaleOrder
from .error_codes import ReturnSaleOrderErrorCode
from .serializers import *
from core.pagination import CustomPagination, ReportPagination
from .services import *


class ReturnSaleOrderListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = ReturnSaleOrderFilter
    search_fields = ["customer__name", "warehouse__name", "lines__product__name"]
    ordering_fields = [
        "created_at",
        "discount_price",
        "customer__name",
        "number",
        "date",
        "created_by__full_name", 
        "updated_by__full_name",
    ]

    @extend_schema(
        responses={200: ReturnSaleOrderSerializer(many=True)},
        description="Retrieve a list of return_sale orders with pagination, search, filtering, and ordering capabilities.",
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
        tags=["return_sale_orders"],
    )
    def get(self, request):
        orders = self.get_queryset()
        orders = self.filter_queryset(request, orders)

        # Paginate results
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)
        serializer = ReturnSaleOrderSerializer(paginated_orders, many=True)
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
            return ReturnSaleOrder.objects.none()
        return get_all_return_sale_orders()


class ReturnSaleOrderDetailView(APIView):
    @extend_schema(
        responses={200: ReturnSaleOrderSerializer},
        description="Retrieve details of a specific return_sale order.",
        tags=["return_sale_orders"],
    )
    def get(self, request, uuid):
        try:
            return_sale_order = get_return_sale_order_by_uuid(uuid)
            serializer = ReturnSaleOrderSerializer(return_sale_order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": ReturnSaleOrderErrorCode.UNKNOWN.value,
                    "message": f" An unexpected error occurred. {str(e)}",
                    "field": "NONE",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReturnSaleOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CreateReturnSaleOrderSerializer,
        responses={201: ReturnSaleOrderSerializer},
        description="Create a new return_sale order.",
        tags=["return_sale_orders"],
    )
    def post(self, request):
        serializer = CreateReturnSaleOrderSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                if isinstance(first_errors, (list, tuple)) and first_errors:
                    message = first_errors[0]
                else:
                    message = str(first_errors) or "Unknown error"
                error_data = {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": message,    
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            return_sale_order = create_return_sale_order(request.user, serializer.validated_data)
            response_serializer = ReturnSaleOrderSerializer(return_sale_order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "Error", "message": f"{e}", "field": "???"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReturnSaleOrderUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UpdateReturnSaleOrderSerializer,
        responses={200: ReturnSaleOrderSerializer},
        description="Update a specific return_sale order.",
        tags=["return_sale_orders"],
    )
    def put(self, request, uuid):
        try:
            return_sale_order = get_return_sale_order_by_uuid(uuid)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateReturnSaleOrderSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": ReturnSaleOrderErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        try:
            updated_order = update_return_sale_order(request.user, return_sale_order, validated_data)
            response_serializer = ReturnSaleOrderSerializer(updated_order)
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


class ReturnSaleOrderDeleteView(APIView):

    @extend_schema(
        responses={204: None},
        description="Soft delete a specific return_sale order.",
        tags=["return_sale_orders"],
    )
    def delete(self, request, uuid):
        try:
            delete_return_sale_order(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
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


class ReturnSaleOrderLinesView(APIView):
    @extend_schema(
        responses={200: ReturnSaleLineSerializer(many=True)},
        description="Retrieve a list of lines for a specific return_sale order.",
        tags=["return_sale_orders"],
    )
    def get(self, request, uuid):
        try:
            return_sale_order = get_return_sale_order_lines(uuid)
            serializer = ReturnSaleLineSerializer(return_sale_order, many=True)
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


class ReturnSaleLineReportView(APIView):
    pagination_class = ReportPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = ReturnSaleLineReportFilter
    search_fields = ["return_sale_order__customer__name", "product__name"]
    ordering_fields = [
        "created_at",
        "total_price",
        "quantity",
        "unit_price",
        "product__name",
        "return_sale_order__date",
        "return_sale_order__customer__name",
        "return_sale_order__number",
        "return_sale_order__warehouse__name",
        "return_sale_order__created_by__full_name",
        "return_sale_order__updated_by__full_name",
    ]

    @extend_schema(
        responses={200: ReturnSaleLineReportSerializer()},
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
                description="Order by fields like `created_at`, `total_price`, `quantity`, `customer_name`, or `return_sale_number`.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample(
                        "Order by customer name",
                        value="return_sale_order__customer__name",
                    ),
                    OpenApiExample(
                        "Order by sale number descending",
                        value="-return_sale_order__number",
                    ),
                    OpenApiExample("Order by quantity descending", value="-quantity"),
                    OpenApiExample("Order by quantity", value="quantity"),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),
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
        tags=["return_sale_lines_report"],
    )
    def get(self, request):
        lines = get_return_sale_line_report(request)

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
        serialized_lines = ReturnSaleLineReportDetailedSerializer(
            paginated_lines, many=True
        )

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
