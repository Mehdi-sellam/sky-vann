from django.forms import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
)
from supplier.error_codes import *
from .services import *
from .error_codes import *
from .filters import *
from core.pagination import CustomPagination
from .models import *
from .serializers import *


class SupplierStatementPDFView(APIView):
    @extend_schema(
        responses={200: dict, 404: dict},
        description="Generate and download supplier statement PDF by customer UUID.",
        tags=["Supplier_Payment"],
        parameters=[
            OpenApiParameter(
                name="start_date",
                description="Start date for statement period (YYYY-MM-DD)",
                required=True,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="end_date",
                description="End date for statement period (YYYY-MM-DD)",
                required=True,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ],
    )
    def get(self, request, supplier_uuid, format=None):
        try:
            supplier = Supplier.objects.get(uuid=supplier_uuid, deleted=False)
        except Supplier.DoesNotExist:
            return Response(
                {
                    "code": "SUPPLIER_NOT_FOUND",
                    "message": f"Supplier with UUID {supplier_uuid} not found.",
                    "field": "supplier_uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get date parameters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            # Call service function
            pdf_response = SupplierStatementService.generate_statement_pdf(
                supplier=supplier, start_date=start_date, end_date=end_date
            )
            return pdf_response

        except Exception as e:
            return Response(
                {
                    "code": "PDF_GENERATION_ERROR",
                    "message": f"Error generating PDF: {str(e)}",
                    "field": "pdf_generation",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# SupplierPayment List View
class SupplierPaymentListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = SupplierPaymentFilter
    search_fields = ["type", "supplier__name", "note"]
    ordering_fields = [
        "created_at",
        "amount",
        "type",
        "method",
        "supplier__name",
        "created_at",
        "note",
        "created_by__full_name",
        "updated_by__full_name",
    ]

    @extend_schema(
        responses={200: SupplierPaymentSerializer(many=True)},
        description="Retrieve a list of supplier payment histories with pagination, search, and ordering.",
        parameters=[
            OpenApiParameter(
                name="page",
                location=OpenApiParameter.QUERY,
                description="Page number for pagination.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                location=OpenApiParameter.QUERY,
                description="Number of results per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="method",
                location=OpenApiParameter.QUERY,
                description="Filter by payment method (e.g., cash, card, cheque, bank_transfer)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="type",
                location=OpenApiParameter.QUERY,
                description="Filter by transaction type (e.g., payment, sale, return_sale)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="min_date",
                location=OpenApiParameter.QUERY,
                description="Start date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="max_date",
                location=OpenApiParameter.QUERY,
                description="End date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="note",
                location=OpenApiParameter.QUERY,
                description="Search in note",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="supplier_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by supplier uuid",
                required=False,
                type=UUID,
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by note or type.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order by fields like `amount` or `created_at`.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by amount", value="amount"),
                    OpenApiExample(
                        "Order by created_at descending", value="-created_at"
                    ),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),

                ],
            ),
        ],
        tags=["Supplier_Payment"],
    )
    def get(self, request, format=None):
        payments = self.get_queryset()
        payments = self.filter_queryset(request, payments)

        # Paginate results
        paginator = self.pagination_class()
        paginated_payments = paginator.paginate_queryset(payments, request)
        serializer = SupplierPaymentSerializer(paginated_payments, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SupplierPayment.objects.none()
        return get_supplier_payment_list()


# SupplierPayment Detail View
class SupplierPaymentDetailView(APIView):
    @extend_schema(
        responses={200: SupplierPaymentSerializer, 404: dict},
        description="Retrieve details of a specific supplier payment history entry by UUID.",
        tags=["Supplier_Payment"],
    )
    def get(self, request, uuid, format=None):
        try:
            history = SupplierPayment.objects.get(uuid=uuid, deleted=False)
        except SupplierPayment.DoesNotExist:
            return Response(
                {
                    "code": SupplierPaymentErrorCode.NOT_FOUND.value,
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SupplierPaymentSerializer(history)
        return Response(serializer.data)


# SupplierPayment Create View
class SupplierPaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=CreateSupplierPaymentSerializer,
        responses={201: SupplierPaymentSerializer, 400: dict},
        description="Create a new supplier payment history entry.",
        tags=["Supplier_Payment"],
    )
    def post(self, request, format=None):
        serializer = CreateSupplierPaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Extract data from the validated serializer
                uuid = serializer.validated_data.get("uuid")
                supplier = serializer.validated_data.get("supplier")
                amount = serializer.validated_data.get("amount")
                payment_type = serializer.validated_data.get(
                    "type", PaymentTypes.PAYMENT.value
                )
                note = serializer.validated_data.get("note")
                payment_method = serializer.validated_data.get(
                    "method", PaymentMethods.CASH.value
                )

                # Call the function to create the supplier payment
                payment = create_supplier_payment(
                    uuid=uuid,
                    supplier=supplier,
                    amount=amount,
                    payment_type=payment_type,
                    payment_method=payment_method,
                    note=note,
                    requester=request.user,
                )

                # Serialize and return the newly created payment
                response_serializer = SupplierPaymentSerializer(payment)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

            except ValueError as e:
                # Handle validation errors from `create_supplier_payment`
                error_data = {
                    "code": "validation_error",
                    "message": str(e),
                    "field": "amount",  # Example: update dynamically based on the context
                }
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

            except SupplierErrorCode as e:
                # Handle specific supplier-related errors
                error_data = {
                    "code": e.code,  # Retrieve the error code from the exception
                    "message": str(e),
                    "field": "supplier",  # Example: adjust dynamically based on the error
                }
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                # Handle unexpected errors
                error_data = {
                    "code": "unexpected_error",
                    "message": f"An unexpected error occurred: {str(e)}",
                }
                return Response(
                    error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Handle invalid serializer input
        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        error_data = {
            "code": "invalid_input",
            "message": first_errors[0] if first_errors else "Invalid input data.",
            "field": first_field,
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)


# SupplierPayment Update View
class SupplierPaymentUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=UpdateSupplierPaymentSerializer,
        responses={200: SupplierPaymentSerializer, 404: dict, 400: dict},
        description="Update an existing supplier payment history entry by UUID.",
        tags=["Supplier_Payment"],
    )
    def put(self, request, uuid, format=None):
        try:
            supplierPayment = SupplierPayment.objects.get(uuid=uuid, deleted=False)
        except SupplierPayment.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UpdateSupplierPaymentSerializer(
            supplierPayment, data=request.data, partial=True
        )
        if serializer.is_valid():
            validated_data = serializer.validated_data
            payment_uuid = uuid
            supplier = supplierPayment.supplier
            new_amount = validated_data.get("amount")
            new_payment_type = supplierPayment.type
            purchase = supplierPayment.purchase
            return_purchase_order = supplierPayment.return_purchase_order
            note = validated_data.get("note", supplierPayment.note)
            payment_method = validated_data.get("method", supplierPayment.method)
            try:
                updated_supplier_payment = update_supplier_payment(
                    payment_uuid=payment_uuid,
                    supplier=supplier,
                    new_amount=new_amount,
                    new_payment_type=new_payment_type,
                    payment_method=payment_method,
                    note=note,
                    purchase=purchase,
                    return_purchase_order=return_purchase_order,
                    requester=request.user,
                )

                response_serializer = SupplierPaymentSerializer(
                    updated_supplier_payment
                )
                return Response(response_serializer.data)
            except ValidationError as ve:
                return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# SupplierPayment Delete View
class SupplierPaymentDeleteView(APIView):
    @transaction.atomic
    @extend_schema(
        responses={204: None, 404: dict},
        description="Soft delete a specific supplier payment history by UUID.",
        tags=["Customer_Payment"],
    )
    def delete(self, request, uuid, format=None):
        try:
            # Fetch the payment history record
            payment = SupplierPayment.objects.get(uuid=uuid, deleted=False)
        except SupplierPayment.DoesNotExist:
            # Return 404 if the payment history doesn't exist
            return Response(
                {
                    "code": "not_found",
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the supplier associated with the payment
        supplier = payment.supplier

        # Soft delete the payment using the service function
        delete_supplier_payment(payment.uuid, supplier)

        # Return a 204 No Content response indicating successful deletion
        return Response(status=status.HTTP_204_NO_CONTENT)
