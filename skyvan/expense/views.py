from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.db import transaction

from .services import get_expense_type_list, get_expenses_list
from .models import ExpenseType, Expense
from .serializers import (
    ExpenseSerializer,
    CreateExpenseSerializer,
    UpdateExpenseSerializer,
    ExpenseTypeSerializer,
    CreateExpenseTypeSerializer,
    UpdateExpenseTypeSerializer,

)
from .filters import ExpenseFilter
from .error_codes import ExpenseErrorCode
from core.pagination import CustomPagination

#  **************** ExpenseTypeView   ****************

#   ExpenseType List View 
class ExpenseTypeListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    @extend_schema(
        responses={200: ExpenseTypeSerializer(many=True)},
        description="Retrieve a list of expense types with pagination, search, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by name or description of the expense type.",
                required=False,
                type=str
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order results by fields. Prefix with `-` for descending order.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by name", value="name"),
                    OpenApiExample("Order by created_at descending", value="-created_at"),
                ]
            ),
        ]
    )
   
    def get(self, request, format=None):
        expense_type = self.get_queryset()
        expense_type = self.filter_queryset(request, expense_type)

        # Paginate results
        paginator = self.pagination_class()
        paginated_status = paginator.paginate_queryset(expense_type, request)
        serializer = ExpenseTypeSerializer(paginated_status, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExpenseType.objects.none()
        return get_expense_type_list()

# ExpenseType Detail View
class ExpenseTypeDetailView(APIView):
    @extend_schema(
        responses={200: ExpenseTypeSerializer, 404: dict},
        description="Retrieve a single expense type by UUID."
    )
    def get(self, request, uuid, format=None):
        try:
            expense_type = ExpenseType.objects.get(uuid=uuid, deleted=False)
        except ExpenseType.DoesNotExist:
            return Response({
                    "code": ExpenseErrorCode.NOT_FOUND.value,
                    "message": f"Expense type with UUID {uuid} not found.",
                    "field": "uuid"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ExpenseTypeSerializer(expense_type)
        return Response(serializer.data)

# ExpenseType Create View
class ExpenseTypeCreateView(APIView):
    @transaction.atomic
    @extend_schema(
        request=CreateExpenseTypeSerializer,
        responses={201: ExpenseTypeSerializer},
        description="Create a new expense type entry."
    )
    def post(self, request, format=None):
        serializer = CreateExpenseTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ExpenseType Update View
class ExpenseTypeUpdateView(APIView):
    @extend_schema(
        request=UpdateExpenseTypeSerializer,
        responses={200: ExpenseTypeSerializer, 404: dict, 400: dict},
        description="Update an existing expense type entry by UUID."
    )
    def put(self, request, uuid, format=None):
        try:
            expense_type = ExpenseType.objects.get(uuid=uuid, deleted=False)
        except ExpenseType.DoesNotExist:
            return Response({
                    "code": ExpenseErrorCode.NOT_FOUND.value,
                    "message": f"Expense type with UUID {uuid} not found.",
                    "field": "uuid"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateExpenseTypeSerializer(expense_type, data=request.data, partial=True)
        if serializer.is_valid():
            expense_type = serializer.save()
            return Response(ExpenseTypeSerializer(expense_type).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ExpenseType Delete View
class ExpenseTypeDeleteView(APIView):
    @transaction.atomic
    @extend_schema(
        responses={204: None, 404: dict},
        description="Soft delete a specific expense type by UUID."
    )
    def delete(self, request, uuid, format=None):
        try:
            expense_type = ExpenseType.objects.get(uuid=uuid, deleted=False)

        except ExpenseType.DoesNotExist:
            return Response({
                    "code": ExpenseErrorCode.NOT_FOUND.value,
                    "message": f"Expense type with UUID {uuid} not found.",
                    "field": "uuid"
                },
                status=status.HTTP_404_NOT_FOUND
            )     
        expense_type.deleted = True
        expense_type.save(update_fields=['deleted'])
        return Response(status=status.HTTP_204_NO_CONTENT)

# **************** Expense View ****************

# Expense View List
class ExpenseListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ExpenseFilter
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'type__name']

    @extend_schema(
        responses={200: ExpenseSerializer(many=True)},
        description="Retrieve a list of expenses with pagination, filtering, search, and ordering capabilities.",
        parameters=[
            OpenApiParameter(name="min_date", location=OpenApiParameter.QUERY, description="Filter expenses from this date (YYYY-MM-DD).", required=False, type=str),
            OpenApiParameter(name="max_date", location=OpenApiParameter.QUERY, description="Filter expenses up to this date (YYYY-MM-DD).", required=False, type=str),
            OpenApiParameter(name="min_amount", location=OpenApiParameter.QUERY, description="Filter expenses with a minimum amount.", required=False, type=float),
            OpenApiParameter(name="max_amount", location=OpenApiParameter.QUERY, description="Filter expenses with a maximum amount.", required=False, type=float),
            OpenApiParameter(name="description", location=OpenApiParameter.QUERY, description="Search by keywords in expense description.", required=False, type=str),
            OpenApiParameter(name="type", location=OpenApiParameter.QUERY, description="Filter expenses by type name.", required=False, type=str),
            OpenApiParameter(name="is_recurring", location=OpenApiParameter.QUERY, description="Filter recurring or non-recurring expenses.", required=False, type=bool),
            OpenApiParameter(name="ordering", location=OpenApiParameter.QUERY, description="Field to use for ordering results.", required=False, type=str, examples=[
                OpenApiExample("Order by date", value="date"),
                OpenApiExample("Order by amount descending", value="-amount"),
                OpenApiExample("Order by type name", value="type__name"),
            ]),
        ]
    )
    
    def get(self, request, format=None):
        expense  = self.get_queryset()
        expense = self.filter_queryset(request, expense)

        # Paginate results
        paginator = self.pagination_class()
        paginated_status = paginator.paginate_queryset(expense, request)
        serializer = ExpenseSerializer(paginated_status, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Expense.objects.none()
        return get_expenses_list()

# Expense View Detail
class ExpenseDetailView(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    @extend_schema(
        responses={200: ExpenseSerializer, 404: dict},
        description="Retrieve a single expense by UUID."
    )
    def get(self, request, uuid, format=None):
        try:
            product = Expense.objects.get(uuid=uuid, deleted=False)
        except Expense.DoesNotExist:
            error_data = {
                "code": ExpenseErrorCode.NOT_FOUND.value,
                "message": f"Expense with UUID {uuid} not found.",
                "field": "UUID."
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)
        serializer = ExpenseSerializer(product)
        return Response(serializer.data)

# Expense View Create
class ExpenseCreateView(APIView):
    @transaction.atomic
    @extend_schema(
        request=CreateExpenseSerializer,
        responses={201: CreateExpenseSerializer},
        description="Create a new expense entry."
    )
    def post(self, request, format=None):
        serializer = CreateExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Expense View Update
class ExpenseUpdateView(APIView):
    @extend_schema(
        request=UpdateExpenseSerializer,
        responses={200: ExpenseSerializer, 400: dict, 404: dict},
        description="Update an existing expense entry by UUID.",
       
    )
    def put(self, request, uuid, format=None):
        try:
            expense = Expense.objects.get(uuid=uuid, deleted=False)
        except Expense.DoesNotExist:
            return Response(
                {
                    "code": ExpenseErrorCode.NOT_FOUND.value,
                    "message": f"Expense with UUID {uuid} not found.",
                    "field": "uuid"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UpdateExpenseSerializer(expense, data=request.data, partial=True)
        if serializer.is_valid():
            expense = serializer.save()
            serializer = ExpenseSerializer(expense)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Expense View Delete
class ExpenseDeleteView(APIView):

    @transaction.atomic
    @extend_schema(
        responses={204: None ,400: dict},
        description="Soft delete a specific expense by UUID."
    )
    def delete(self, request, uuid, format=None):
        try:
            expense = Expense.objects.get(uuid=uuid, deleted=False)
        except Expense.DoesNotExist:
            return Response({
                    "code": ExpenseErrorCode.NOT_FOUND.value,
                    "message": f"Expense with UUID {uuid} not found.",
                    "field": "UUID."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        expense.deleted = True
        expense.save(update_fields=['deleted'])
        return Response(status=status.HTTP_204_NO_CONTENT)


