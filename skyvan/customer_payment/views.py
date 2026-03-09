from django.forms import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiTypes
from customer.error_codes import *
from .services import *
from .error_codes import *
from .filters import *
from core.pagination import CustomPagination
from .models import *
from .serializers import *
from django.db.models import Q



class CustomerStatementPDFView(APIView):
    @extend_schema(
        responses={200: dict, 404: dict},
        description="Generate and download customer statement PDF by customer UUID.",
        tags=["Customer_Payment"],
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
    def get(self, request, customer_uuid, format=None):
        try:
            customer = Customer.objects.get(uuid=customer_uuid, deleted=False)
        except Customer.DoesNotExist:
            return Response(
                {
                    "code": "CUSTOMER_NOT_FOUND",
                    "message": f"Customer with UUID {customer_uuid} not found.",
                    "field": "customer_uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            # Call service function
            pdf_response = ClientStatementService.generate_statement_pdf(
                customer=customer,
                start_date=start_date,
                end_date=end_date
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

# CustomerPayment List View
class CustomerPaymentListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = CustomerPaymentFilter
    search_fields = ["type", "customer__name", "note"]
    ordering_fields = [
        "created_at",
        "amount",
        "type",
        "method",
        "customer__name",
        "created_at",
        "note",
        "created_by__full_name",
        "updated_by__full_name",
    ]

    @extend_schema(
        responses={200: CustomerPaymentSerializer(many=True)},
        description="Retrieve a list of customer payment histories with pagination, search, and ordering.",
        parameters=[
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
                name="customer_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by customer uuid",
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
                description="Order by one of the available fields. Use `-` prefix for descending order.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by amount ascending", value="amount"),
                    OpenApiExample("Order by amount descending", value="-amount"),
                    OpenApiExample("Order by created_at ascending", value="created_at"),
                    OpenApiExample(
                        "Order by created_at descending", value="-created_at"
                    ),
                    OpenApiExample("Order by type ascending", value="type"),
                    OpenApiExample("Order by type descending", value="-type"),
                    OpenApiExample("Order by method ascending", value="method"),
                    OpenApiExample("Order by method descending", value="-method"),
                    OpenApiExample(
                        "Order by customer name ascending", value="customer__name"
                    ),
                    OpenApiExample(
                        "Order by customer name descending", value="-customer__name"
                    ),
                    OpenApiExample("Order by note ascending", value="note"),
                    OpenApiExample("Order by note descending", value="-note"),
                    OpenApiExample(
                        "Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'",
                        value="created_by__full_name",
                    ),
                    OpenApiExample(
                        "Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'",
                        value="updated_by__full_name",
                    ),
                ],
            ),
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
        ],
        tags=["Customer_Payment"],
    )
    def get(self, request, format=None):

        payments = self.get_queryset()
        payments = self.filter_queryset(request, payments)

        # Paginate results
        paginator = self.pagination_class()
        paginated_payments = paginator.paginate_queryset(payments, request)
        serializer = CustomerPaymentSerializer(paginated_payments, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CustomerPayment.objects.none()
        return get_customer_payments_list()

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset


# CustomerPayment Detail View
class CustomerPaymentDetailView(APIView):
    @extend_schema(
        responses={200: CustomerPaymentSerializer, 404: dict},
        description="Retrieve details of a specific customer payment history entry by UUID.",
        tags=["Customer_Payment"],
    )
    def get(self, request, uuid, format=None):
        try:
            history = CustomerPayment.objects.get(uuid=uuid, deleted=False)
        except CustomerPayment.DoesNotExist:
            return Response(
                {
                    "code": CustomerPaymentErrorCode.NOT_FOUND.value,
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CustomerPaymentSerializer(history)
        return Response(serializer.data)


# CustomerPayment Create View
class CustomerPaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=CreateCustomerPaymentSerializer,
        responses={201: CustomerPaymentSerializer, 400: dict},
        description="Create a new customer payment history entry.",
        tags=["Customer_Payment"],
    )
    def post(self, request, format=None):
        serializer = CreateCustomerPaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Extract data from the validated serializer
                uuid = serializer.validated_data.get("uuid")
                customer = serializer.validated_data.get("customer")
                amount = serializer.validated_data.get("amount")
                payment_type = serializer.validated_data.get(
                    "type", PaymentTypeEnum.PAYMENT.value
                )
                note = serializer.validated_data.get("note")
                payment_method = serializer.validated_data.get(
                    "method", PaymentMethods.CASH.value
                )

                # Call the function to create the customer payment
                payment = create_customer_payment(
                    uuid=uuid,
                    customer=customer,
                    amount=amount,
                    payment_type=payment_type,
                    payment_method=payment_method,
                    note=note,
                    requester=request.user,
                )

                # Serialize and return the newly created payment
                response_serializer = CustomerPaymentSerializer(payment)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

            except ValueError as e:
                # Handle validation errors from `create_customer_payment`
                error_data = {
                    "code": "validation_error",
                    "message": str(e),
                    "field": "amount",  # Example: update dynamically based on the context
                }
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

            except CustomerErrorCode as e:  # type: ignore
                # Handle specific customer-related errors
                error_data = {
                    "code": e.code,  # Retrieve the error code from the exception # type: ignore
                    "message": str(e),
                    "field": "customer",  # Example: adjust dynamically based on the error
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


# CustomerPayment Update View
class CustomerPaymentUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=UpdateCustomerPaymentSerializer,
        responses={200: CustomerPaymentSerializer, 404: dict, 400: dict},
        description="Update an existing customer payment history entry by UUID.",
        tags=["Customer_Payment"],
    )
    def put(self, request, uuid, format=None):
        try:
            customerPayment = CustomerPayment.objects.get(uuid=uuid, deleted=False)
        except CustomerPayment.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UpdateCustomerPaymentSerializer(
            customerPayment, data=request.data, partial=True
        )
        if serializer.is_valid():
            validated_data = serializer.validated_data
            payment_uuid = uuid
            customer = customerPayment.customer
            new_amount = validated_data.get("amount")
            new_payment_type = customerPayment.type
            sale = customerPayment.sale
            return_sale_order = customerPayment.return_sale_order
            note = validated_data.get("note", customerPayment.note)
            payment_method = validated_data.get("method", customerPayment.method)
            try:
                updated_customer_payment = update_customer_payment(
                    payment_uuid=payment_uuid,
                    customer=customer,
                    new_amount=new_amount,
                    new_payment_type=new_payment_type,
                    payment_method=payment_method,
                    note=note,
                    sale=sale,
                    return_sale_order=return_sale_order,
                    updater=request.user,
                )
                response_serializer = CustomerPaymentSerializer(
                    updated_customer_payment
                )
                return Response(response_serializer.data)
            except ValidationError as ve:
                return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# CustomerPayment Delete View
class CustomerPaymentDeleteView(APIView):
    @transaction.atomic
    @extend_schema(
        responses={204: None, 404: dict},
        description="Soft delete a specific customer payment history by UUID.",
        tags=["Customer_Payment"],
    )
    def delete(self, request, uuid, format=None):
        try:
            # Fetch the payment history record
            payment = CustomerPayment.objects.get(uuid=uuid, deleted=False)
        except CustomerPayment.DoesNotExist:
            # Return 404 if the payment history doesn't exist
            return Response(
                {
                    "code": "not_found",
                    "message": f"Payment history with UUID {uuid} not found.",
                    "field": "uuid",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the customer associated with the payment
        customer = payment.customer

        # Soft delete the payment using the service function
        delete_customer_payment(payment.uuid, customer)

        # Return a 204 No Content response indicating successful deletion
        return Response(status=status.HTTP_204_NO_CONTENT)


# Status List View
class StatusListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = CustomerPaymentFilter
    search_fields = ["type", "customer__name", "note"]
    ordering_fields = ["created_at", "amount"]

    @extend_schema(
        responses={200: StatusSerializer(many=True)},
        description="Retrieve a list of Status histories with pagination, search, and ordering.",
        parameters=[
            OpenApiParameter(
                name="customer_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter by customer uuid",
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
        ],
        tags=["Customer_Payment"],
    )
    def get(self, request, format=None):

        status = self.get_queryset()
        status = self.filter_queryset(request, status)

        # Paginate results
        paginator = self.pagination_class()
        paginated_status = paginator.paginate_queryset(status, request)
        serializer = StatusSerializer(paginated_status, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CustomerPayment.objects.none()
        return get_status()
