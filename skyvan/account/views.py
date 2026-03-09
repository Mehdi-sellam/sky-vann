from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter,OpenApiResponse, OpenApiExample
from .serializers import (
    OrganizationUserSerializer,
    OrganizationUserCreateSerializer,
    OrganizationUserUpdateSerializer,
    CustomLoginSerializer,
    UserLoginResponseSerializer,
    OrganizationMeUpdateSerializer,
)
from .services import (
    get_all_organization_users,
    create_organization_user, 
    update_organization_user,
    delete_organization_user,
    get_organization_user_by_uuid,
)
from core.pagination import CustomPagination
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from .filters import OrganizationUserFilter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    APIException,
    PermissionDenied,
)
from .error_codes import UserErrorCode
from .models import User
from rest_framework.permissions import IsAuthenticated


# 🔹 List Organization Users
class OrganizationUserListView(APIView):
    """
    API view to list all organization users with pagination, filtering, searching, and ordering.
    """

    pagination_class = CustomPagination
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = OrganizationUserFilter
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = [
        "created_at",
        "first_name",
        "last_name",
        "email",
        "phone",
        "is_active",
    ]

    @extend_schema(
        summary="List Organization Users",
        description="Retrieve a list of organization users with pagination, filtering, search, and ordering.",
        responses={200: OrganizationUserSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="ordering",
                location=OpenApiParameter.QUERY,
                description="Order the results using specified fields.",
                required=False,
                type=str,
                examples=[
                    OpenApiExample("By First Name", value="first_name"),
                    OpenApiExample("By Last Name", value="-last_name"),
                    OpenApiExample("By Email", value="email"),
                    OpenApiExample("By Phone", value="-phone"),
                    OpenApiExample("By Organization", value="organization__name"),
                ],
            ),
            OpenApiParameter(
                name="search",
                location=OpenApiParameter.QUERY,
                description="Search users by first name, last name, email, phone, or organization name.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="is_active",
                location=OpenApiParameter.QUERY,
                description="Filter users based on active status (true/false).",
                required=False,
                type=bool,
                examples=[
                    OpenApiExample("Active Users", value=True),
                    OpenApiExample("Inactive Users", value=False),
                ],
            ),
        ],
    )
    def get(self, request, format=None):
        """Retrieve all organization users with pagination, filtering, searching, and ordering."""
        users = self.get_queryset()
        users = self.filter_queryset(request, users)

        # Apply pagination
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = OrganizationUserSerializer(paginated_users, many=True)
        return paginator.get_paginated_response(serializer.data)

    def filter_queryset(self, request, queryset):
        """
        Apply filtering, searching, and ordering using backends.
        """
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return get_all_organization_users()

class OrganizationUserDetailsView(APIView):

    @extend_schema(
        responses={200: OrganizationUserSerializer},
        description="Retrieve details of a specific user.",
    )
    def get(self, request, uuid, format=None):

        try:
            user = get_organization_user_by_uuid(uuid)
            serializer = OrganizationUserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:

            print(f"Unexpected error: {e}")
            return Response(
                {"code": "unknown_error", "message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class OrganizationUserCreateView(APIView):
    """API view to create a new organization user."""

    @extend_schema(
        summary="Create Organization User",
        description="Creates a new user associated with an organization.",
        request=OrganizationUserCreateSerializer,
        responses={201: OrganizationUserSerializer},
    )
    def post(self, request):
        """Create a new organization user."""
        serializer = OrganizationUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": UserErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = create_organization_user(serializer.validated_data)
            response_serializer = OrganizationUserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except APIException as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": UserErrorCode.SERVER_ERROR,
                    "message": f"{e}",
                    "field": "???",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# 🔹 Update Organization User (PUT/PATCH)
class OrganizationUserUpdateView(APIView):
    """API view to update an organization user."""

    @extend_schema(
        summary="Update Organization User",
        description="Updates an existing organization user by UUID.",
        request=OrganizationUserUpdateSerializer,
        responses={200: OrganizationUserSerializer},
    )
    def put(self, request, uuid):
        """Handles full update (PUT) of an organization user."""
        try:

            user = get_organization_user_by_uuid(uuid)
        except NotFound as ve:
            return Response(ve.detail, status=status.HTTP_404_NOT_FOUND)

        serializer = OrganizationUserUpdateSerializer(user, data=request.data)
        if not serializer.is_valid():
            first_field, first_errors = next(
                iter(serializer.errors.items()), (None, [])
            )
            if first_field:
                error_data = {
                    "code": UserErrorCode.NOT_FOUND.value,
                    "message": first_errors[0] if first_errors else "Unknown error",
                    "field": first_field,
                }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        try:
            print(type(request.user))
            print(request.organisation_id)
            user = update_organization_user(
                user=user,
                validated_data=serializer.validated_data,
                requestor=request.user,
            )

            response_serializer = OrganizationUserSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as ve:
            return Response(ve.detail, status=status.HTTP_403_FORBIDDEN)
        except APIException as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": UserErrorCode.SERVER_ERROR.value,
                    "message": f"{e}",
                    "field": "???",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# 🔹 Soft Delete Organization User
class OrganizationUserDeleteView(APIView):
    """API view to soft delete an organization user."""

    @extend_schema(
        summary="Soft Delete Organization User",
        description="Marks an organization user as deleted without removing them from the database.",
        responses={204: None},
    )
    def delete(self, request, uuid):
        """Handles soft deletion of an organization user."""
        try:

            delete_organization_user(uuid=uuid, requestor=request.user)
            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response(e.detail, status=status.HTTP_403_FORBIDDEN)
        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)
        except APIException as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {
                    "code": UserErrorCode.SERVER_ERROR.value,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "field": "general",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class CustomLoginView(generics.GenericAPIView):
    serializer_class = CustomLoginSerializer
    @extend_schema(
        summary="Custom Login",
        description="Handles user login and returns a token.",
        request=CustomLoginSerializer,
        responses={200: UserLoginResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        response_serializer = UserLoginResponseSerializer( data  )
        return Response(response_serializer.data)

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'access': {'type': 'string', 'description': 'New access token'}
                    }
                },
                description='Access token refreshed successfully'
            ),
            400: OpenApiResponse(
                response={
                    'type': 'object',
                    'properties': {
                        'error': {'type': 'string'}
                    }
                },
                description='Invalid refresh token or validation error'
            )
        },
        examples=[
            OpenApiExample(
                "Successful Refresh",
                value={"access": "new_access_token_here"},
                response_only=True,
                status_codes=["200"]
            ),
            OpenApiExample(
                "Invalid Token",
                value={"error": "Token is invalid or expired"},
                response_only=True,
                status_codes=["400"]
            ),
        ]
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'access': serializer.validated_data['access'],
            },
            status=status.HTTP_200_OK,
        )
        
        
class OrganizationMeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update Own Profile",
        request=OrganizationMeUpdateSerializer,
        responses={200: OrganizationUserSerializer},
    )
    def put(self, request):
        """Update the authenticated user's profile."""
        user = request.user
        serializer = OrganizationMeUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            response_serializer = OrganizationUserSerializer(user)
            
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        # Custom error formatting 
        error_data = {
            "code": UserErrorCode.VALIDATION_ERROR.value,
            "message": next(iter(serializer.errors.values()))[0],
            "field": next(iter(serializer.errors.keys())),
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
    
class OrganizationMeRetrieveView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="Get Current User",
        description="Returns the authenticated user's details.",
        responses={200: OrganizationUserSerializer}, 
    )
    def get(self, request,   ):

        try: 
            serializer = OrganizationUserSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NotFound as e:
            return Response(e.detail, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:

            print(f"Unexpected error: {e}")
            return Response(
                {"code": "unknown_error", "message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
