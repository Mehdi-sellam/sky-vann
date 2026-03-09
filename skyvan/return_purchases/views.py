from drf_spectacular.types import OpenApiTypes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from .services import *
from .models import *
from .error_codes import ReturnPurchaseOrderErrorCode
from .serializers import *
from core.pagination import CustomPagination, ReportPagination
from .filters import ReturnPurchaseOrderFilter, ReturnPurchaseLineReportFilter
from django.db.models import Sum, DecimalField


class ReturnPurchaseOrderListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = ReturnPurchaseOrderFilter
    search_fields = ["supplier__name", "lines__product__name"]
    ordering_fields = ["created_at", "total_price", "supplier__name", "date", "number", "created_by__full_name", "updated_by__full_name"]

    @extend_schema(
        responses={200: ReturnPurchaseOrderSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Ordering results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("By date", value="date"),
                    OpenApiExample("By -total_price", value="-total_price"),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),
                ],
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by supplier name or product name.",
                required=False,
                type=str,
            ),
        ],
        description="Retrieve a list of return_purchase orders with pagination, search, filtering, and ordering.",
    )
    def get(self, request):
        orders = self.get_queryset()
        orders = self.filter_queryset(request, orders)

        # Paginate results
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)
        serializer = ReturnPurchaseOrderSerializer(paginated_orders, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReturnPurchaseOrder.objects.none()
        return get_return_purchases_list()


class CreateReturnPurchaseOrderView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=CreateReturnPurchaseOrderSerializer,
        responses={201: ReturnPurchaseOrderSerializer},
        description="Create a new return_purchase order.",
    )
    def post(self, request):
        serializer = CreateReturnPurchaseOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            return_purchase_order = create_return_purchase_order(
                request.user,
                serializer.validated_data
            )
            response_serializer = ReturnPurchaseOrderSerializer(return_purchase_order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "Error", "message": f"{e}", "field": "???"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReturnPurchaseOrderDetailView(APIView):

    @extend_schema(
        responses={200: ReturnPurchaseOrderSerializer},
        description="Retrieve details of a specific return_purchase order.",
    )
    def get(self, request, uuid):
        try:
            return_purchase_order = ReturnPurchaseOrder.objects.get(
                uuid=uuid, deleted=False
            )
        except ReturnPurchaseOrder.DoesNotExist:
            error_data = {
                "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"ReturnPurchase Order with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = ReturnPurchaseOrderSerializer(return_purchase_order)
        return Response(serializer.data)


class UpdateReturnPurchaseOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UpdateReturnPurchaseOrderSerializer,
        responses={200: ReturnPurchaseOrderSerializer},
        description="Update a specific return_purchase order.",
    )
    def put(self, request, uuid):
        try:
            return_purchase_order = ReturnPurchaseOrder.objects.get(
                uuid=uuid, deleted=False
            )
        except ReturnPurchaseOrder.DoesNotExist:
            error_data = {
                "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"ReturnPurchase Order with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateReturnPurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            try:
                update_return_purchase = update_return_purchase_order(
                    request.user, return_purchase_order, validated_data
                )
                response_serializer = ReturnPurchaseOrderSerializer(
                    update_return_purchase
                )
                return Response(response_serializer.data)
            except ValidationError as ve:
                return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteReturnPurchaseOrderView(APIView):

    @extend_schema(
        responses={204: None}, description="Soft delete a specific return_sale order."
    )
    def delete(self, request, uuid):
        try:
            delete_return_purchase_order(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ReturnPurchaseOrder.DoesNotExist:
            error_data = {
                "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"ReturnSale Order with UUID {uuid} not found.",
                "field": "UUID",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class ReturnPurchaseOrderLinesView(APIView):

    serializer_class = ReturnPurchaseLineSerializer

    @extend_schema(
        responses={200: ReturnPurchaseLineSerializer(many=True)},
        description="Retrieve a list of lines for a specific return_purchase order.",
    )
    def get(self, request, uuid):
        try:
            return_purchase_order = ReturnPurchaseOrder.objects.get(
                uuid=uuid, deleted=False
            )
        except ReturnPurchaseOrder.DoesNotExist:
            error_data = {
                "code": ReturnPurchaseOrderErrorCode.NOT_FOUND.value,
                "message": f"ReturnPurchase Order with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        return_purchase_lines = return_purchase_order.lines.all()
        serializer = ReturnPurchaseLineSerializer(return_purchase_lines, many=True)
        return Response(serializer.data)


class ReturnPurchaseLineReportView(APIView):
    pagination_class = ReportPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = ReturnPurchaseLineReportFilter
    search_fields = ["return_purchase_order__supplier__name", "product__name"]
    ordering_fields = [
        "total_price",
        "quantity",
        "unit_price",
        "product__name",
        "return_purchase_order__date"
        "return_purchase_order__supplier__name",  # Order by Supplier Name
        "return_purchase_order__number",
        "return_purchase_order__warehouse__name" ,
    ]

    @extend_schema(
        responses={200: ReturnPurchaseLineReportSerializer()},
        description="Retrieve a list of return purchase lines with pagination, search, filtering, ordering, and total calculations.",
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
                description="Order by fields like `created_at`, `total_price`, `quantity`, `supplier_name`, or `return_purchase_number`.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by total_price descending", value="-total_price"
                    ),
                    OpenApiExample(
                        "Order by supplier name",
                        value="return_purchase_order__supplier__name",
                    ),
                    OpenApiExample(
                        "Order by return purchase number descending",
                        value="-return_purchase_order__number",
                    ),
                    OpenApiExample("Order by quantity descending", value="-quantity"),
                    OpenApiExample("Order by quantity", value="quantity"),
                ],
            ),
            OpenApiParameter(
                name="date_after",
                location=OpenApiParameter.QUERY,
                description="Filter by return purchase order creation date (after this date).",
                required=False,
                type=str,
                examples=[OpenApiExample("After January 1, 2024", value="2024-01-01")],
            ),
            OpenApiParameter(
                name="date_before",
                location=OpenApiParameter.QUERY,
                description="Filter by return purchase order creation date (before this date).",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Before January 31, 2024", value="2024-01-31")
                ],
            ),
        ],
        tags=["return_purchase_lines_report"],
    )
    def get(self, request):
        lines = get_return_purchase_line_report(request)

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
        serialized_lines = ReturnPurchaseLineReportDetailedSerializer(
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
