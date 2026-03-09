from django.urls import path
from .views import (
    VanListView,
    VanCreateView,
    VanDetailView,
    VanUpdateView,
    VanDeleteView,
    VanAssignmentCreateView,
    VanAssignmentCloseView,
    VanAssignmentUpdateView,
    VanAssignmentListView,
    VanAssignmentDeleteView,
    VanAssignmentDetailView,
    VanInventoryListView,
    MyVanInventoryListView,
)

urlpatterns = [
    path("vans/", VanListView.as_view(), name="van-list"),
    path("vans/create/", VanCreateView.as_view(), name="van-create"),
    path("vans/<uuid:uuid>/", VanDetailView.as_view(), name="van-detail"),
    path("vans/<uuid:uuid>/update/", VanUpdateView.as_view(), name="van-update"),
    path("vans/<uuid:uuid>/delete/", VanDeleteView.as_view(), name="van-delete"),
    path(
        "vans/assignments/create/",
        VanAssignmentCreateView.as_view(),
        name="van-assignment-create",
    ),
    path(
        "assignments/<uuid:uuid>/close/",
        VanAssignmentCloseView.as_view(),
        name="van-assignment-close",
    ),
    path("vans/assignments/<uuid:uuid>/update/", VanAssignmentUpdateView.as_view()),
    path("vans/assignments/", VanAssignmentListView.as_view()),
    path(
        "vans/assignments/<uuid:uuid>/delete/",
        VanAssignmentDeleteView.as_view(),
        name="van-assignment-delete",
    ),
    path(
        "vans/assignments/<uuid:uuid>/",
        VanAssignmentDetailView.as_view(),
        name="van-assignment-detail",
    ),
    path(
        "vans/<uuid:van_uuid>/inventory/",
        VanInventoryListView.as_view(),
        name="van-inventory-list",
    ),
        path(
        "vans/inventory/my/",
        MyVanInventoryListView.as_view(),
        name="my-van-inventory-list",
    ),
]
