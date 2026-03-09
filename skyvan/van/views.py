from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Van, VanInventory
from .serializers import (
    VanSerializer,
    VanCreateSerializer,
    VanUpdateSerializer,
    CreateVanAssignmentSerializer,
    VanAssignmentSerializer,
    UpdateVanAssignmentSerializer,
    VanInventorySerializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
)
from .services import (
    create_van,
    get_my_inventory,
    get_user_active_assignment,
    update_van,
    delete_van,
    get_van_by_uuid,
    get_van_list,
    create_van_assignment,
    get_van_assignment_by_uuid,
    close_van_assignment,
    update_van_assignment,
    get_all_van_assignments,
    delete_van_assignment,
    get_van_inventory_by_van_uuid,
)
from .error_codes import VanErrorCode
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from core.pagination import CustomPagination
from .filters import VanFilter, VanAssignmentFilter, VanInventoryFilter
from .enums import VanStatus
from uuid import UUID
from rest_framework.permissions import IsAuthenticated

class VanListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = VanFilter
    search_fields = ["name", "license_plate"]
    ordering_fields = ["created_at", "name", "license_plate", "capacity", "status"]

    @extend_schema(
        responses={200: VanSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search in name or license plate.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[OpenApiExample("Partial match", value="123ABC")],
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                description="Filter vans by status. Available values: active, inactive, sold, broken.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Active", value=VanStatus.ACTIVE),
                    OpenApiExample("InActive", value=VanStatus.INACTIVE),
                    OpenApiExample("Sold", value=VanStatus.SOLD),
                    OpenApiExample("Broken", value=VanStatus.BROKEN),
                ],
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample("Order by name descending", value="-name"),
                    OpenApiExample("Order by capacity ascending", value="capacity"),
                ],
            ),
            OpenApiParameter(
                name="license_plate",
                location=OpenApiParameter.QUERY,
                description="Filter vans by license plate (case-insensitive partial match).",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Search by plate", value="DZ-123"),
                ],
            ),
            OpenApiParameter(
                name="is_working",
                location=OpenApiParameter.QUERY,
                description="Filter vans by working status. true = currently assigned, false = not working.",
                required=False,
                type=OpenApiTypes.BOOL,
                examples=[
                    OpenApiExample("Working vans", value=True),
                    OpenApiExample("Idle vans", value=False),
                ],
            ),
        ],
        description="List all active vans with pagination, search, filtering, and ordering support. You can order by created_at, name, license_plate, or capacity.",
        tags=["van"],
    )
    
    def get(self, request, format=None):
        vans = self.get_queryset()
        vans = self.filter_queryset(request, vans)

        paginator = self.pagination_class()
        paginated_vans = paginator.paginate_queryset(vans, request)
        serializer = VanSerializer(paginated_vans, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            from van.models import Van

            return Van.objects.none()
        return get_van_list()


class VanCreateView(APIView):
    @extend_schema(
        request=VanCreateSerializer,
        responses={201: VanSerializer},
        description="Create a new delivery van.",
        tags=["van"],
    )
    def post(self, request):
        serializer = VanCreateSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": VanErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            van = create_van(serializer.validated_data)
            return Response(VanSerializer(van).data, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanDetailView(APIView):
    @extend_schema(
        responses={200: VanSerializer},
        description="Retrieve details of a specific van by UUID.",
        tags=["van"],
    )
    def get(self, request, uuid):
        try:
            van = get_van_by_uuid(uuid)
            return Response(VanSerializer(van).data, status=status.HTTP_200_OK)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanUpdateView(APIView):
    @extend_schema(
        request=VanUpdateSerializer,
        responses={200: VanSerializer},
        description="Update an existing van's details.",
        tags=["van"],
    )
    def put(self, request, uuid):
        try:
            van = get_van_by_uuid(uuid)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = VanUpdateSerializer(instance=van, data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": VanErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_van = update_van(van, serializer.validated_data)
            return Response(VanSerializer(updated_van).data, status=status.HTTP_200_OK)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanDeleteView(APIView):
    @extend_schema(
        responses={204: None},
        description="Soft delete a van (only if no active assignment or stock).",
        tags=["van"],
    )
    def delete(self, request, uuid):
        try:
            delete_van(uuid)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanAssignmentCreateView(APIView):
    @extend_schema(
        request=CreateVanAssignmentSerializer,
        responses={201: VanAssignmentSerializer},
        description="Assign a user to a van for a time period.",
        tags=["van"],
    )
    def post(self, request):
        serializer = CreateVanAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": VanErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = create_van_assignment(serializer.validated_data)
            return Response(
                VanAssignmentSerializer(assignment).data,
                status=status.HTTP_201_CREATED,
            )
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as er:
            return Response(er.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"message": f"Error assigning user to van: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanAssignmentCloseView(APIView):
    serializer_class = VanAssignmentSerializer
    @extend_schema(
        description="Close a van assignment (mark it as completed). This will set end_datetime to now and mark it as inactive.",
        responses={200: VanAssignmentSerializer},
        tags=["van"],
    )
    def post(self, request, uuid):
        try:
            assignment = get_van_assignment_by_uuid(uuid)
            closed_assignment = close_van_assignment(assignment)
            return Response(
                VanAssignmentSerializer(closed_assignment).data,
                status=status.HTTP_200_OK,
            )

        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van_assignment",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanAssignmentUpdateView(APIView):
    @extend_schema(
        request=UpdateVanAssignmentSerializer,
        responses={200: VanAssignmentSerializer},
        description="Update an existing van assignment (only start_datetime, end_datetime, and notes can be modified).",
        tags=["van"],
    )
    def put(self, request, uuid):
        try:
            assignment = get_van_assignment_by_uuid(uuid)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateVanAssignmentSerializer(
            assignment, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated = update_van_assignment(assignment, serializer.validated_data)
            return Response(
                VanAssignmentSerializer(updated).data, status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van_assignment",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanAssignmentListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = VanAssignmentFilter
    search_fields = ["user__username", "van__name"]
    ordering_fields = ["start_datetime", "end_datetime", "created_at"]

    @extend_schema(
        responses={200: VanAssignmentSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by user name or van name.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[OpenApiExample("Search by username", value="ahmed")],
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order results by start_datetime, end_datetime, or created_at.",
                required=False,
                type=OpenApiTypes.STR,
                examples=[
                    OpenApiExample("Order by start time", value="start_datetime"),
                    OpenApiExample("Order by newest", value="-created_at"),
                ],
            ),
            OpenApiParameter(
                name="is_active",
                location=OpenApiParameter.QUERY,
                description="Filter by active status (true = current assignment, false = closed).",
                required=False,
                type=OpenApiTypes.BOOL,
                examples=[
                    OpenApiExample("Active only", value=True),
                    OpenApiExample("Inactive only", value=False),
                ],
            ),
            OpenApiParameter(
                name="van_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter assignments by van UUID.",
                required=False,
                type=OpenApiTypes.UUID,
                examples=[
                    OpenApiExample(
                        "Filter by van", value="3fa85f64-5717-4562-b3fc-2c963f66afa6"
                    )
                ],
            ),
            OpenApiParameter(
                name="user_uuid",
                location=OpenApiParameter.QUERY,
                description="Filter assignments by user UUID.",
                required=False,
                type=OpenApiTypes.UUID,
                examples=[
                    OpenApiExample(
                        "Filter by user", value="e215b6b3-bbdf-45c2-89b2-2e4b4694bb5f"
                    )
                ],
            ),
            OpenApiParameter(
                name="start_after",
                location=OpenApiParameter.QUERY,
                description="Filter assignments that start after a specific datetime.",
                required=False,
                type=OpenApiTypes.DATETIME,
                examples=[OpenApiExample("Start after", value="2025-04-01T00:00:00Z")],
            ),
            OpenApiParameter(
                name="start_before",
                location=OpenApiParameter.QUERY,
                description="Filter assignments that start before a specific datetime.",
                required=False,
                type=OpenApiTypes.DATETIME,
                examples=[OpenApiExample("Start before", value="2025-04-15T23:59:59Z")],
            ),
            OpenApiParameter(
                name="end_after",
                location=OpenApiParameter.QUERY,
                description="Filter assignments that end after a specific datetime.",
                required=False,
                type=OpenApiTypes.DATETIME,
                examples=[OpenApiExample("End after", value="2025-04-10T00:00:00Z")],
            ),
            OpenApiParameter(
                name="end_before",
                location=OpenApiParameter.QUERY,
                description="Filter assignments that end before a specific datetime.",
                required=False,
                type=OpenApiTypes.DATETIME,
                examples=[OpenApiExample("End before", value="2025-04-20T00:00:00Z")],
            ),
        ],
        description="List all van assignments with pagination, search, filtering, and ordering support. You can filter by van, user, active status, and date ranges.",
        tags=["van"],
    )
    def get(self, request, format=None):
        assignments = self.get_queryset()
        assignments = self.filter_queryset(request, assignments)

        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(assignments, request)
        serializer = VanAssignmentSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):

            from van.models import VanAssignment

            return VanAssignment.objects.none()
        return get_all_van_assignments()


class VanAssignmentDeleteView(APIView):
    @extend_schema(
        description="Soft delete a van assignment. Only allowed if assignment is not active.",
        responses={200: VanAssignmentSerializer},
        tags=["van"],
    )
    def delete(self, request, uuid):

        try:
            assignment = get_van_assignment_by_uuid(uuid)
            delete_van_assignment(assignment)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except NotFound as nf:
            return Response(nf.detail, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"code": "server_error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanAssignmentDetailView(APIView):
    @extend_schema(
        description="Retrieve detailed information for a specific van assignment.",
        responses={200: VanAssignmentSerializer},
        tags=["van"],
    )
    def get(self, request, uuid: UUID):
        try:
            assignment = get_van_assignment_by_uuid(uuid)
            return Response(
                VanAssignmentSerializer(assignment).data, status=status.HTTP_200_OK
            )
        except NotFound as nf:
            return Response(nf.detail, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {
                    "code": VanErrorCode.SERVER_ERROR.value,
                    "message": f"Unexpected error: {str(e)}",
                    "field": "van_assignment",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VanInventoryListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = VanInventoryFilter
    search_fields = ["product__name"]
    ordering_fields = ["quantity", "created_at"]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="van_uuid",
                location=OpenApiParameter.PATH,
                description="Van UUID to fetch inventory for.",
                required=True,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search by product name.",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order by quantity or created_at.",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: VanInventorySerializer(many=True)},
        tags=["van"],
        description="List inventory items for a specific van (by van UUID) with pagination, search and ordering.",
    )
    def get(self, request, van_uuid):
        inventories = self.get_queryset(van_uuid)
        inventories = self.filter_queryset(request, inventories)

        paginator = self.pagination_class()
        paginated = paginator.paginate_queryset(inventories, request)
        serializer = VanInventorySerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)


    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self, van_uuid=None):
        if getattr(self, "swagger_fake_view", False):
            return VanInventory.objects.none() 
        van = get_van_by_uuid(van_uuid)
        return get_van_inventory_by_van_uuid(van)

# class MyVanAssignmentListView(APIView):
class MyVanInventoryListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: VanInventorySerializer(many=True)},
        tags=["van"],
        description="List inventory items for the van assigned to the authenticated user.",
    )
    def get(self, request):
        inventories = get_my_inventory(request.user)
        serializer = VanInventorySerializer(inventories, many=True)
        return Response(serializer.data)
    
    
    
# class VanList(APIView):

#     permission_classes = [IsAuthenticated]

#     def get(self, request, format=None):
#         last_sync_time = request.query_params.get("last_sync_time")
#         if last_sync_time:
#             vans = Van.objects.filter(last_synced_at__gt=last_sync_time)
#         else:
#             vans = Van.objects.all()
#         serializer = VanSerializer(vans, many=True)
#         return Response(serializer.data)


# class SyncVan(APIView):

#     permission_classes = [IsAuthenticated]

#     def post(self, request, format=None):
#         vans_payload = request.data
#         user = request.user

#         success, data = sync_model(Van, vans_payload, user, serializer=VanSerializer)
#         if success:
#             return Response(data, status=status.HTTP_201_CREATED)
#         else:
#             return Response(data, status=status.HTTP_400_BAD_REQUEST)
