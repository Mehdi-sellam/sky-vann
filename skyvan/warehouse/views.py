from rest_framework.views import APIView

from .services import get_warhouses_list

from .filters import WarehouseFilter
from .models import Warehouse
from .error_codes import WarhouseErrorCode
from core.pagination import CustomPagination
from .serializers import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample


class WarehouseListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = WarehouseFilter
    search_fields = ["name", "location"]
    ordering_fields = ["created_at", "updated_at", "name", "location"]

    @extend_schema(
        description="Retrieve a list of warehouse with pagination, search, filtering, and ordering capabilities. Available ordering fields: created_at, updated_at, name, location.",
        responses={200: WarehouseSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by created_at", value="created_at"),
                    OpenApiExample("Order by name descending", value="-name"),
                    OpenApiExample("Order by location", value="location"),
                    OpenApiExample(
                        "Order by updated_at descending", value="-updated_at"
                    ),
                ],
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search query for filtering results.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="name",
                location=OpenApiParameter.QUERY,
                description="Filter results where name contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="location",
                location=OpenApiParameter.QUERY,
                description="Filter results where location contains this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter results where created_at is greater than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter results where created_at is less than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="updated_at_after",
                location=OpenApiParameter.QUERY,
                description="Filter results where updated_at is greater than or equal to this value.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="updated_at_before",
                location=OpenApiParameter.QUERY,
                description="Filter results where updated_at is less than or equal to this value.",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, format=None):
        warhouses = self.get_queryset()
        warhouses = self.filter_queryset(request, warhouses)
        
        
        # Paginate results
        paginator = self.pagination_class()
        paginated_warhouses = paginator.paginate_queryset(warhouses, request)
        serializer = WarehouseSerializer(paginated_warhouses, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def filter_queryset(self, request, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Warehouse.objects.none()
        return get_warhouses_list()

# View to create a new warehouse
class WarehouseCreateView(APIView):
    @extend_schema(
        request=WarehouseCreateUpdateSerializer,  # Serializer used for request body
        responses={
            201: WarehouseCreateUpdateSerializer,  # Response in case of success
            400: dict,  # Error response in case of validation failure
        },
        description="Create a new warehouse entry.",
        examples=[
            OpenApiExample(
                "Successful Warehouse Creation",
                value={
                    "uuid": "01f24106-f4e9-40a9-87ec-50de8314309d",
                    "name": "Main Warehouse",
                    "location": "123 Industrial Avenue",
                },
                status_codes=["201"],
            ),
            OpenApiExample(
                "Validation Error",
                value={
                    "name": ["This field is required."],
                    "location": ["This field cannot be blank."],
                },
                status_codes=["400"],
            ),
        ],
    )
    # POST request for creating a new warehouse
    def post(self, request, *args, **kwargs):
        # Manually instantiate the serializer with the request data
        serializer = WarehouseCreateUpdateSerializer(data=request.data)

        # Validate the data
        if serializer.is_valid():
            # Save the new warehouse
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # If validation fails, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# View to retrieve, update, and delete a specific warehouse by UUID
class WarehouseDetailView(APIView):

    def get_object(self, uuid):
        try:
            # Retrieve the warehouse by UUID
            return Warehouse.objects.get(uuid=uuid, deleted=False)
        except Warehouse.DoesNotExist:
            return None

    @extend_schema(
        responses={200: WarehouseCreateUpdateSerializer, 404: dict},
        parameters=[
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.PATH,
                description="Unique identifier of the warehouse",
                required=True,
                type=str,
            )
        ],
        description="Retrieve the details of a specific warehouse by UUID.",
    )
    # GET: Retrieve a warehouse by UUID
    def get(self, request, uuid, *args, **kwargs):
        warehouse = self.get_object(uuid)
        if not warehouse:
            return Response(
                {"error": "Warehouse not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = WarehouseCreateUpdateSerializer(warehouse)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=WarehouseCreateUpdateSerializer,
        responses={200: WarehouseCreateUpdateSerializer, 400: dict, 404: dict},
        parameters=[
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.PATH,
                description="Unique identifier of the warehouse to be updated",
                required=True,
                type=str,
            )
        ],
        description="Update the details of a specific warehouse by UUID.",
        examples=[
            OpenApiExample(
                "Successful Update",
                value={
                    "name": "Updated Warehouse",
                    "location": "456 New Location Street",
                    "capacity": 1500,
                },
                status_codes=["200"],
            ),
            OpenApiExample(
                "Validation Error",
                value={"error": "A warehouse with this name already exists."},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Warehouse Not Found",
                value={"error": "Warehouse not found."},
                status_codes=["404"],
            ),
        ],
    )

    # PUT: Update a warehouse by UUID
    def put(self, request, uuid, *args, **kwargs):
        warehouse = self.get_object(uuid)
        if not warehouse:
            return Response(
                {"error": "Warehouse not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if a warehouse with the same name exists (except the current one)
        if (
            Warehouse.objects.filter(name=request.data.get("name"))
            .exclude(uuid=uuid)
            .exists()
        ):
            return Response(
                {"error": "A warehouse with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Manually update the warehouse with the new data
        serializer = WarehouseCreateUpdateSerializer(warehouse, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={204: None, 404: dict},
        parameters=[
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.PATH,
                description="Unique identifier of the warehouse to be deleted",
                required=True,
                type=str,
            )
        ],
        description="Soft delete a specific warehouse by UUID.",
        examples=[
            OpenApiExample(
                "Successful Deletion",
                value={"message": "Warehouse deleted."},
                status_codes=["204"],
            ),
            OpenApiExample(
                "Warehouse Not Found",
                value={"error": "Warehouse not found."},
                status_codes=["404"],
            ),
        ],
    )

    # DELETE: Soft delete a warehouse by UUID
    def delete(self, request, uuid, *args, **kwargs):
        warehouse = self.get_object(uuid)
        if not warehouse:
            return Response(
                {"error": "Warehouse not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Soft delete by setting `deleted=True`
        warehouse.deleted = True
        warehouse.save()
        return Response(
            {"message": "Warehouse deleted."}, status=status.HTTP_204_NO_CONTENT
        )


class WarehouseInventoryListView(APIView):
    pagination_class = CustomPagination

    @extend_schema(
        responses={200: WarehouseInventorySerializer(many=True), 404: dict},
        parameters=[
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.PATH,
                description="Unique identifier of the warehouse to fetch inventory for.",
                required=True,
                type=str,
            )
        ],
        description="Retrieve a paginated list of inventory items for a specific warehouse by UUID.",
        examples=[
            OpenApiExample(
                "Successful Retrieval",
                value={
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "item": "Item 1",
                            "quantity": 10,
                            "price_per_unit": "15.50",
                            "total_value": "155.00",
                        },
                        {
                            "item": "Item 2",
                            "quantity": 20,
                            "price_per_unit": "5.00",
                            "total_value": "100.00",
                        },
                    ],
                },
                status_codes=["200"],
            ),
            OpenApiExample(
                "Warehouse Not Found",
                value={
                    "code": "warehouse_not_found",
                    "message": "Warehouse with UUID <UUID> not found.",
                    "field": "UUID.",
                },
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request, uuid, format=None):

        try:
            warehouse = Warehouse.objects.get(uuid=uuid, deleted=False)
        except Warehouse.DoesNotExist:
            error_data = {
                "code": WarhouseErrorCode.NOT_FOUND.value,
                "message": f"Warehouse with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        warhouse_inventory = warehouse.inventory.filter(deleted=False)

        paginator = self.pagination_class()
        paginated_warhouse_inventory = paginator.paginate_queryset(
            warhouse_inventory, request
        )
        serializer = WarehouseInventorySerializer(
            paginated_warhouse_inventory, many=True
        )
        return paginator.get_paginated_response(serializer.data)


class InventoryListView(APIView):
    pagination_class = CustomPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]
    search_fields = ["product__name"]  # Adjust this to the actual product name field
    ordering_fields = [
        "created_at",
        "updated_at",
        "product__name",
    ]  # Add any other relevant fields here

    @extend_schema(
        description="Retrieve inventory for a specific warehouse with pagination, search, and ordering capabilities.",
        responses={200: InventorySerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search query for filtering results by product name.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Field to use for ordering results. Use `-` prefix for descending order.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("Order by product name", value="product__name"),
                    OpenApiExample(
                        "Order by created_at descending", value="-created_at"
                    ),
                    OpenApiExample("Order by updated_at", value="updated_at"),
                ],
            ),
        ],
    )
    def get(self, request, uuid, format=None):
        try:
            warehouse = Warehouse.objects.get(uuid=uuid, deleted=False)
        except Warehouse.DoesNotExist:
            error_data = {
                "code": WarhouseErrorCode.NOT_FOUND.value,
                "message": f"Warehouse with UUID {uuid} not found.",
                "field": "UUID.",
            }
            return Response(error_data, status=status.HTTP_404_NOT_FOUND)

        # Fetch inventory items and apply search and ordering
        warehouse_inventory = warehouse.inventory.filter(deleted=False)

        # Apply search
        search_backend = drf_filters.SearchFilter()
        searched_inventory = search_backend.filter_queryset(
            request, warehouse_inventory, self
        )

        # Apply ordering
        ordering_backend = drf_filters.OrderingFilter()
        ordered_inventory = ordering_backend.filter_queryset(
            request, searched_inventory, self
        )

        # Apply pagination
        paginator = self.pagination_class()
        paginated_inventory = paginator.paginate_queryset(ordered_inventory, request)
        serializer = InventorySerializer(paginated_inventory, many=True)

        return paginator.get_paginated_response(serializer.data)


class CentralInventoryView(APIView):
    pagination_class = CustomPagination
    search_fields = ["product__name"]  # Adjust this to the actual product name field
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter]

    @extend_schema(
        responses={200: CentralInventorySerializer(many=True)},
        description="Retrieve a paginated list of all central inventory items.",
        parameters=[
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search query for filtering results by product name.",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, format=None):
        central_inventory = CentralInventory.objects.all()
        # Apply search
        search_backend = drf_filters.SearchFilter()
        central_inventory = search_backend.filter_queryset(
            request, central_inventory, self
        )
        paginator = self.pagination_class()
        paginated_central_inventory = paginator.paginate_queryset(
            central_inventory, request
        )
        serializer = CentralInventorySerializer(paginated_central_inventory, many=True)
        return paginator.get_paginated_response(serializer.data)
