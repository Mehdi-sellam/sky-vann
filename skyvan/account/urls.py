from django.urls import path


from .views import (
    CustomLoginView,
    OrganizationUserListView,
    OrganizationUserCreateView,
    OrganizationUserUpdateView,
    OrganizationUserDeleteView,
    OrganizationUserDetailsView,
    CustomTokenRefreshView,
    OrganizationMeUpdateView,
    OrganizationMeRetrieveView,
)

urlpatterns = [
    path("create_token/", CustomLoginView.as_view(), name="create_token"),
    path("token_refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("me/update/", OrganizationMeUpdateView.as_view(), name="update_user"),
    path("me/", OrganizationMeRetrieveView.as_view(), name="retrieve_user"),
    

    path(
        "organization-users/<uuid:uuid>/",
        OrganizationUserDetailsView.as_view(),
        name="organization-user-detail",
    ),
    path(
        "organization-users/",
        OrganizationUserListView.as_view(),
        name="organization-users-list",
    ),
    path(
        "organization-users/add/",
        OrganizationUserCreateView.as_view(),
        name="organization-users-create",
    ),
    path(
        "organization-users/<uuid:uuid>/update/",
        OrganizationUserUpdateView.as_view(),
        name="organization-users-update",
    ),
    path(
        "organization-users/<uuid:uuid>/delete/",
        OrganizationUserDeleteView.as_view(),
        name="organization-users-delete",
    ),
]
