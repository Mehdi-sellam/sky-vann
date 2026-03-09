
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from .services import *
from .models import *
from .serializers import *
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from history.utils import add_history_record
from .models import Customer
from .error_codes import CustomerErrorCode
from core.pagination import CustomPagination
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

class SyncCustomer(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    @extend_schema(
        description="Synchronize multiple customers. If a customer exists, it updates it; otherwise, it creates a new one.",
        request=CustomerSerializer(many=True),
        responses={
            201: CustomerSerializer(many=True),
            400: {"description": "Invalid data or validation errors"},
        }
    )
    def post(self, request, format=None):
        customers_payload = request.data
        user = request.user
        # Keep track of successfully added/updated customers
        successes = []
        with transaction.atomic():
            for customer_payload in customers_payload:
                # Check if the customer already exists in the database based on UUID
                try:
                    customer = Customer.objects.get(
                        uuid=customer_payload['uuid'])
                except Customer.DoesNotExist:
                    customer = None

                if customer and customer.updated_at >= datetime.fromisoformat(customer_payload['updated_at']):
                    continue
                old_instance = None
                if customer:
                    old_instance = Customer(
                        **{field.name: getattr(customer, field.name) for field in customer._meta.fields})
                # Add or update customer based on whether it already exists
                customer_payload['last_synced_at'] = timezone.now()
                customer_payload['updated_at'] = timezone.now()
                if not customer:

                    serializer = CustomerSerializer(data=customer_payload)
                else:
                    serializer = CustomerSerializer(
                        customer, data=customer_payload)
                if serializer.is_valid():

                    instance = serializer.save()
                    successes.append(serializer.data)
                    action = 'create' if not customer else 'update'

                    add_history_record(user, instance, old_instance, action)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': 'Customers synchronized successfully', 'data': successes}, status=status.HTTP_201_CREATED)


class CustomerListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]
    search_fields = ['name', 'email','phone', 'address']  # Allows searching by name or email
    ordering_fields = ['name', 'email','phone', 'address', 'created_at', 'updated_at']  # Allows ordering by specified fields
    @extend_schema(
        description="Retrieve a list of customers with pagination, search, and ordering capabilities.",
        responses={200: CustomerSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search query for filtering by name or email.",
                required=False,
                type=str
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Field to use for ordering results. Use `-` prefix for descending order.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by name", value="name"),
                    OpenApiExample("Order by email descending", value="-email"),
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample("Order by updated_at descending", value="-updated_at"),
                ]
            ),
        ],
    )
    def get(self, request, format=None):
        # Filter by deleted=False by default
        customers = Customer.objects.filter(deleted=False).order_by('-created_at')

        # Apply search
        search_backend = drf_filters.SearchFilter()
        searched_customers = search_backend.filter_queryset(request, customers, self)

        # Apply ordering
        ordering_backend = drf_filters.OrderingFilter()
        ordered_customers = ordering_backend.filter_queryset(request, searched_customers, self)

        # Paginate the searched and ordered queryset
        paginator = self.pagination_class()
        paginated_customers = paginator.paginate_queryset(ordered_customers, request)
        serializer = CustomerSerializer(paginated_customers, many=True)
        
        return paginator.get_paginated_response(serializer.data)


class CustomerDetailView(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        description="Retrieve detailed information for a specific customer by UUID.",
        responses={200: CustomerSerializer,404: {"description": "Customer not found"}
        },
    )
    def get(self, request, uuid, format=None):
        try:
            customer = Customer.objects.get(uuid=uuid, deleted=False)
        except Customer.DoesNotExist:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message": f"Customer with UUID {uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

class CustomerCreateView(APIView):
    @extend_schema(
        description="Create a new customer.",
        request=CreateCustomerSerializer,
        responses={
            201: CustomerSerializer,
            400: {"description": "Validation errors or invalid data"}
        }
    )
    def post(self, request, format=None):
        try:
            customer = create_customer(request.data)
            serializer = CustomerSerializer(customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Return structured error response
            error_data = {
                "code": e.detail.get('code', CustomerErrorCode.NOT_FOUND.value),
                "message": e.detail.get('message', "Validation error"),
                "field": e.detail.get('field', None),
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

class CustomerUpdateView(APIView):
    @extend_schema(
        description="Update an existing customer by UUID.",
        request=UpdateCustomerSerializer,
        responses={
            200: CustomerSerializer,
            404: {"description": "Customer not found"},
            400: {"description": "Validation errors or invalid data"}
        }
    )
    def put(self, request, uuid, format=None):
        try:
            customer = update_customer(uuid, request.data)
            serializer = CustomerSerializer(customer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            # Return structured error response
            error_data = {
                "code": e.detail.get('code', CustomerErrorCode.NOT_FOUND.value),
                "message": e.detail.get('message', "Validation error"),
                "field": e.detail.get('field', None),
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)


class CustomerDeleteView(APIView):
    @extend_schema(
        description="Soft delete a customer by UUID, marking it as deleted without removing it from the database.",
        responses={
            204: None,
            404: {"description": "Customer not found"}
        }
    )
    def delete(self, request, uuid, format=None):
        try:
            delete_customer(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            # Return structured error response
            error_data = {
                "code": e.detail.get('code', CustomerErrorCode.NOT_FOUND.value),
                "message": e.detail.get('message', "Validation error"),
                "field": e.detail.get('field', None),
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

class ContactCreateView(APIView):
    @extend_schema(
        description="Create a new contact for a specific customer by UUID.",
        request=ContactSerializer,
        responses={
            201: ContactSerializer,
            400: {"description": "Validation errors or invalid data"},
            404: {"description": "Customer not found"}
        }
    )
    def post(self, request, customer_uuid, format=None):
        try:
            # Fetch the customer object based on the 'customer_uuid'
            customer = Customer.objects.get(uuid=customer_uuid, deleted=False)
        except Customer.DoesNotExist:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message": f"Customer with UUID {customer_uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        # # Create a contact associated with the specific client
        data = request.data
        data['customer'] = customer.uuid  # Associate the contact with the client
        serializer = ContactSerializer(data=data)

        if serializer.is_valid():
            # Check for an existing contact with the same email
            email = serializer.validated_data.get('email')

            try:
                # Fetch the customer object based on the 'customer_uuid'
                c = Contact.objects.get(email=email)
                error_data = {
                    "code": CustomerErrorCode.ALREADY_EXISTS.value,
                    "message": "Contact with Email address already exists.",
                    "field": "email"
                }
                return Response(error_data, status=status.HTTP_404_NOT_FOUND)

            except Contact.DoesNotExist:
                pass

            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        first_field, first_errors = next(
            iter(serializer.errors.items()), (None, []))
        if first_field:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message":  first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class ContactDetailView(APIView):
    @extend_schema(
        description="Retrieve details of a specific contact by UUID.",
        responses={
            200: ContactSerializer,
            404: {"description": "Contact not found"}
        }
    )
    def get(self, request, uuid, format=None):
        try:
            contact = Contact.objects.get(uuid=uuid, deleted=False)
        except Contact.DoesNotExist:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message": f"Customer with UUID {uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        serializer = ContactSerializer(contact)
        return Response(serializer.data)


class ContactsListView(APIView):
    pagination_class = CustomPagination
    @extend_schema(
        description="Retrieve a list of contacts associated with a specific customer.",
        responses={200: ContactSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="customer_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter contacts by customer UUID.",
                required=False,
                type=str
            ),
        ],
    )
    def get(self, request, format=None):
        customer_uuid = request.query_params.get('customer_uuid')

        contacts = Contact.objects.filter(
            customer__uuid=customer_uuid, deleted=False)
        paginator = self.pagination_class()
        paginated_contact = paginator.paginate_queryset(contacts, request)

        serializer = ContactSerializer(paginated_contact, many=True)
        return paginator.get_paginated_response(serializer.data)


class ContactUpdateView(APIView):
    @extend_schema(
        description="Update a contact by UUID.",
        request=UpdateContactSerializer,
        responses={
            200: ContactSerializer,
            400: {"description": "Validation errors or invalid data"},
            404: {"description": "Contact not found"}
        }
    )
    def put(self, request, uuid, format=None):
        try:
            contact = Contact.objects.get(uuid=uuid, deleted=False)
        except Contact.DoesNotExist:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message": f"Contact with UUID {uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateContactSerializer(contact, data=request.data)
        if serializer.is_valid():
            # Next, check if an entry with the same email address already exists
            email = serializer.validated_data.get('email')
            existing_contact = Contact.objects.filter(email=email).exclude(
                uuid=contact.uuid if contact else None).first()
            if existing_contact:
                error_data = {
                    "code": CustomerErrorCode.ALREADY_EXISTS.value,
                    "message": "Contact with this Email address already exists.",
                    "field": "email"
                }
                return Response(error_data, status=status.HTTP_404_NOT_FOUND)

            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContactDeleteView(APIView):
    @extend_schema(
        description="Soft delete a contact by UUID, marking it as deleted without removing it from the database.",
        responses={
            204: None,
            404: {"description": "Contact not found"}
        }
    )
    def delete(self, request, uuid, format=None):
        try:
            contact = Contact.objects.get(uuid=uuid, deleted=False)
        except Contact.DoesNotExist:
            error_data = {
                "code": CustomerErrorCode.NOT_FOUND.value,
                "message": f"Contact with UUID {uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        contact.deleted = True
        contact.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
