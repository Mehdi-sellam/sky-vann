from drf_spectacular.types import OpenApiTypes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services import (
    get_all_purchase_orders,
    get_purchase_order_by_uuid,
    update_purchase_order,
    create_purchase_order,
    delete_purchase_order,
    get_purchase_order_lines,
    get_purchase_line_report,
)
from .models import *
from rest_framework.views import APIView
from .error_codes import PurchaseOrderErrorCode
from .serializers import *
from core.pagination import CustomPagination, ReportPagination

from .filters import PurchaseOrderFilter, PurchaseLineReportFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework.exceptions import ValidationError, NotFound, APIException
from django.db.models import Sum, DecimalField


class PurchaseOrderView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = PurchaseOrderFilter
    search_fields = ["supplier__name", "lines__product__name", "number"]
    ordering_fields = ["created_at", "total_price", "supplier__name", "number", "date", "created_by__full_name", "updated_by__full_name"]

    @extend_schema(
        responses={200: PurchaseOrderSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Example 1", value="created_at"),
                    OpenApiExample("Example 1", value="-created_at"),
                    OpenApiExample("Example 2", value="-total_price"),
                    OpenApiExample("Example 2", value="+total_price"),
                    OpenApiExample("Example 3", value="supplier__name"),
                    OpenApiExample("Example 3", value="-supplier__name"),
                    OpenApiExample("by number", value="-number"),
                    OpenApiExample("by number", value="number"),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),
                ],
            ),
        ],
        description="Retrieve a list of purchase orders with pagination, search, filtering, and ordering capabilities. Available ordering fields: created_at, total_price, supplier__name.",
    )
    def get(self, request, format=None):
        ordered_orders = self.get_queryset()
        ordered_orders = self.filter_queryset(request, ordered_orders)

        # Apply pagination
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(ordered_orders, request)
        serializer = PurchaseOrderSerializer(paginated_orders, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PurchaseOrder.objects.none()
        return get_all_purchase_orders()

    def filter_queryset(self, request, queryset):
        """
        Apply filter, search, and ordering using backends.
        """
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    @extend_schema(
        request=CreatePurchaseOrderSerializer,
        responses={201: PurchaseOrderSerializer},
        description="Create a new purchase order.",
    )
    def post(self, request, format=None):

        # Initialize serializer
        serializer = CreatePurchaseOrderSerializer(data=request.data)
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
                    "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": message,
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            purchase_order = create_purchase_order(request.user, serializer.validated_data)
            response_serializer = PurchaseOrderSerializer(purchase_order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "Error", "message": f"{e}", "field": "???"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseOrderDetails(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PurchaseOrderSerializer},
        description="Retrieve details of a specific purchase order.",
    )
    def get(self, request, uuid, format=None):

        try:
            purchase_order = get_purchase_order_by_uuid(uuid)
            serializer = PurchaseOrderSerializer(purchase_order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:

            print(f"Unexpected error: {e}")
            return Response(
                {"code": "unknown_error", "message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=UpdatePurchaseOrderSerializer,
        responses={200: PurchaseOrderSerializer},
        description="Update a specific purchase order.",
    )
    def put(self, request, uuid, format=None):
        try:
            purchase_order = get_purchase_order_by_uuid(uuid)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdatePurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            try:
                update_purchase = update_purchase_order(request.user, purchase_order, validated_data)
                response_serializer = PurchaseOrderSerializer(update_purchase)
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

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={204: None}, description="Soft delete a specific purchase order."
    )
    def delete(self, request, uuid, format=None):

        try:
            delete_purchase_order(uuid)
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


class PurchaseOrderLinesView(APIView):
    serializer_class = PurchaseLineSerializer

    @extend_schema(
        responses={200: PurchaseLineSerializer(many=True)},
        description="Retrieve a list of lines for a specific purchase order.",
    )
    def get(self, request, uuid, format=None):

        try:
            purchase_lines = get_purchase_order_lines(uuid)
            serializer = PurchaseLineSerializer(purchase_lines, many=True)
            return Response(serializer.data)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": PurchaseOrderErrorCode.NOT_FOUND.value,
                    "message": f"Purchase Order with UUID {uuid} not found.",
                    "field": "UUID.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseLineReportView(APIView):
    pagination_class = ReportPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = PurchaseLineReportFilter
    search_fields = ["purchase_order__supplier__name", "product__name"]
    ordering_fields = [
        "purchase_order__date",
        "total_price",
        "quantity",
        "unit_price",
        "product__name",
        "purchase_order__supplier__name",
        "sale_order__warehouse__name"  # Order by Supplier Name
        "purchase_order__number",
    ]

    @extend_schema(
        responses={200: PurchaseLineReportSerializer()},
        description="Retrieve a list of purchase lines with pagination, search, filtering, ordering, and total calculations.",
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
                name="supplier_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by supplier UUID.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Filter by a specific supplier",
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
                description="Search by supplier name or product name.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order by fields like `created_at`, `total_price`, `quantity`, `supplier_name`, or `purchase_number`.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample("Order by created_at", value="date"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample(
                        "Order by supplier name", value="purchase_order__supplier__name"
                    ),
                    OpenApiExample(
                        "Order by purchase number descending",
                        value="-purchase_order__number",
                    ),
                    OpenApiExample("Order by quantity descending", value="-quantity"),
                    OpenApiExample("Order by quantity", value="quantity"),
                ],
            ),
            OpenApiParameter(
                name="date_after",
                location=OpenApiParameter.QUERY,
                description="Filter by purchase order creation date (after this date).",
                required=False,
                type=str,
                examples=[OpenApiExample("After January 1, 2024", value="2024-01-01")],
            ),
            OpenApiParameter(
                name="date_before",
                location=OpenApiParameter.QUERY,
                description="Filter by purchase order creation date (before this date).",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Before January 31, 2024", value="2024-01-31")
                ],
            ),
        ],
        tags=["purchase_lines_report"],
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
        serialized_lines = PurchaseLineReportDetailedSerializer(
            paginated_lines, many=True
        )

        # Return response using PurchaseLinePagination
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

        products = self.get_queryset()
        products = self.filter_queryset(request, products)

        # Paginate results
        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_queryset(self, request):
        if getattr(self, "swagger_fake_view", False):
            return PurchaseLine.objects.none()
        return get_purchase_line_report(request)
