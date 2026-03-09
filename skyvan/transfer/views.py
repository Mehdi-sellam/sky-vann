from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.pagination import CustomPagination
from .error_codes import TransferErrorCode
from .filters import TransferFilter
from .services import (
    accept_transfer,
    delete_transfer,
    get_transfer_lines,
    get_transfer_list,
    get_transfer_by_uuid,
    create_transfer,
    mark_transfer_as_draft,
    mark_transfer_as_pending,
    reject_transfer,
    reverse_and_clone_transfer,
    update_transfer,
    get_my_transfer,
    )
from .serializers import (
    TransferSerializer,
    CreateTransferSerializer,
    RejectTransferSerializer,
    UpdateTransferSerializer,
    TransferLineSerializer,
    MyTransferSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
)
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

class TransferListView(APIView):
    """
    List all transfers with filtering, search, and ordering.
    """

    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = TransferFilter
    search_fields = ["transfer_type"]
    ordering_fields = ["created_at", "updated_at",  "created_by__full_name", "updated_by__full_name"]

    @extend_schema(
        description="Retrieve a list of transfers with filtering, search, and ordering capabilities.",
        responses={200: TransferSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by transfer type.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[OpenApiExample("Search", value="van_to_warehouse")],
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order results by created_at or updated_at.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample(
                        "Order by updated_at descending", value="-updated_at"
                    ),
                    OpenApiExample("Order by created_by ASC, For DESC oredering add ' - ' like this: '-created_by__full_name'", value="created_by__full_name"),
                    OpenApiExample("Order by updated_by ASC, For DESC oredering add ' - 'like this: '-updated_by__full_name'", value="updated_by__full_name"),
                ],
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                description="Filter by status (pending, accepted, completed, rejected).",
                required=False,
                type=OpenApiTypes.STR,
                examples=[OpenApiExample("Accepted", value="accepted")],
            ),
            OpenApiParameter(
                name="source_van",
                location=OpenApiParameter.QUERY,
                description="Filter by source van UUID.",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="destination_van",
                location=OpenApiParameter.QUERY,
                description="Filter by destination van UUID.",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="source_warehouse",
                location=OpenApiParameter.QUERY,
                description="Filter by source warehouse UUID.",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="destination_warehouse",
                location=OpenApiParameter.QUERY,
                description="Filter by destination warehouse UUID.",
                required=False,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="created_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter transfers created after this date.",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="created_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter transfers created before this date.",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="updated_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter transfers updated after this date.",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="updated_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter transfers updated before this date.",
                required=False,
                type=OpenApiTypes.DATE,
            ),
        ],
        tags=["Transfer"],
    )
    def get(self, request, format=None):
        print(request.user)
        transfers = self.get_queryset()
        transfers = self.filter_queryset(request, transfers)

        paginator = self.pagination_class()
        paginated_transfers = paginator.paginate_queryset(transfers, request)
        serializer = TransferSerializer(paginated_transfers, many=True)
        return paginator.get_paginated_response(serializer.data)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            from .models import Transfer

            return Transfer.objects.none()
        return get_transfer_list(self.request)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset


class TransferDetailView(APIView):

    @extend_schema(
        description="Retrieve detailed information for a specific transfer by UUID.",
        responses={200: TransferSerializer, 404: {"description": "Transfer not found"}},
        tags=["Transfer"],
    )
    def get(self, request, uuid, format=None):
        try:
            transfer = get_transfer_by_uuid(uuid)
        except NotFound:
            return Response(
                {"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = TransferSerializer(transfer)
        return Response(serializer.data)


class TransferCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Create a new transfer.",
        request=CreateTransferSerializer,
        responses={
            201: TransferSerializer,
            400: {"description": "Validation errors or invalid data"},
        },
        tags=["Transfer"],
    )
    def post(self, request, format=None):
        serializer = CreateTransferSerializer(data=request.data)
        if serializer.is_valid():
            transfer = create_transfer(request.user, **serializer.validated_data)
            return Response(
                TransferSerializer(transfer).data, status=status.HTTP_201_CREATED
            )

        first_field, first_errors = next(iter(serializer.errors.items()), (None, []))
        if first_field:
            error_data = {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)


class RejectTransferView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=RejectTransferSerializer,
        responses={200: TransferSerializer},
        description="Reject a pending transfer.",
        tags=["Transfer"],
    )
    def post(self, request, uuid):
        try:
            transfer = get_transfer_by_uuid(uuid)
            reason = request.data.get("reason", "")
            rejected = reject_transfer(request.user, transfer, reason)
            return Response(
                TransferSerializer(rejected).data, status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except NotFound as ve:
            return Response(ve.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": TransferErrorCode.SERVER_ERROR.value,
                    "message": str(e),
                    "field": "transfer",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AcceptTransferView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransferSerializer  
    @extend_schema(
        description="Accept a transfer and update stock accordingly. Only allowed if status is pending.",
        responses={200: TransferSerializer},
        request=None, 
        tags=["Transfer"],
    )
    def post(self, request, uuid):
        try:
            transfer = get_transfer_by_uuid(uuid)
            updated_transfer = accept_transfer(request.user, transfer)

            return Response(
                self.serializer_class(updated_transfer).data,
                status=status.HTTP_200_OK,
            )

        except NotFound as nf:
            return Response(
                nf.detail,
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": TransferErrorCode.SERVER_ERROR,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "transfer",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransferUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        description="Update a draft or pending transfer by UUID.",
        request=UpdateTransferSerializer,
        responses={200: TransferSerializer, 400: dict, 404: dict},
        tags=["Transfer"],
    )
    def put(self, request, uuid):
        serializer = UpdateTransferSerializer(data=request.data)
        if not serializer.is_valid():
            if (
                isinstance(serializer.errors, dict)
                and {"code", "message", "field"} <= serializer.errors.keys()
            ):
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Default fallback: extract first error field
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            error_data = {
                "code": TransferErrorCode.NOT_FOUND.value,
                "message": first_errors[0] if first_errors else "Unknown error",
                "field": first_field,
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        try:
            transfer = update_transfer(request.user, uuid, serializer.validated_data)
            return Response(
                TransferSerializer(transfer).data, status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)


class TransferDeleteView(APIView):
    serializer_class = None
    @extend_schema(
        description="Soft delete a pending transfer by UUID. Only allowed if status is still pending.",
        tags=["Transfer"],
        responses={204: OpenApiTypes.NONE}, 
    )
    def delete(self, request, uuid):
        try:
            transfer = get_transfer_by_uuid(uuid)
            delete_transfer(transfer)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": TransferErrorCode.SERVER_ERROR.value,
                    "message": str(e),
                    "field": "transfer",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransferReverseAndCloneView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransferSerializer

    @extend_schema(
        description="Reverse an accepted transfer and create a new clone as pending.",
        responses={200: TransferSerializer},
        tags=["Transfer"],
    )
    def post(self, request, uuid):

        try:
            original_transfer = get_transfer_by_uuid(uuid)
            cloned_transfer = reverse_and_clone_transfer(
                request.user,
                original_transfer
            )  # Ignore the reversal
            return Response(
                TransferSerializer(cloned_transfer).data,
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": TransferErrorCode.SERVER_ERROR.value,
                    "message": str(e),
                    "field": "transfer",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TransferLinesView(APIView):
    @extend_schema(
        responses={200: TransferLineSerializer(many=True)},
        description="Retrieve a list of lines for a specific sale order.",
        tags=["Transfer"],
    )
    def get(self, request, uuid):

        sale_lines = get_transfer_lines(request, uuid)
        serializer = TransferLineSerializer(sale_lines, many=True)
        return Response(serializer.data)


class TransferMarkAsDraftView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransferSerializer
    @extend_schema(
        description="Mark a transfer as draft.",
        responses={200: TransferSerializer, 400: dict, 404: dict},
        tags=["Transfer"],
    )
    def post(self, request, uuid):
        try:
            transfer = mark_transfer_as_draft(request.user, uuid)
            return Response(
                TransferSerializer(transfer).data, status=status.HTTP_200_OK
            )

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class TransferMarkAsPendingView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransferSerializer

    @extend_schema(
        description="Mark a transfer as pending.",
        responses={200: TransferSerializer, 400: dict, 404: dict},
        tags=["Transfer"],
    )
    def post(self, request, uuid):
        try:
            transfer = mark_transfer_as_pending(request.user, uuid)
            return Response(
                TransferSerializer(transfer).data, status=status.HTTP_200_OK
            )

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class MyTransfersView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="List transfer lines where user is assigned to the destination van of a pending transfer.",
        responses={200: MyTransferSerializer(many=True)},
        tags=["Transfer"],
    )
    def get(self, request):
        my_transfer = get_my_transfer(request)
        serializer = MyTransferSerializer(my_transfer, many=True)
        return Response(serializer.data, status=200)
    
    
    
    