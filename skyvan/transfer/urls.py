from django.urls import path
from .views import  (
    TransferListView,
    TransferCreateView,
    TransferDetailView,
    TransferUpdateView,
    TransferDeleteView,
    MyTransfersView,
    TransferLinesView,
    RejectTransferView,
    AcceptTransferView,
    TransferReverseAndCloneView,
    TransferMarkAsDraftView,
    TransferMarkAsPendingView,
)

urlpatterns = [
    path("transfers/", TransferListView.as_view(), name="transfer_list"),
    path("transfers/my/", MyTransfersView.as_view(), name="my_transfers"),
    path("transfers/create/", TransferCreateView.as_view(), name="transfer_create"),
    path("transfers/<uuid:uuid>/", TransferDetailView.as_view(), name="transfer_detail"
    ),
    path(
        "transfers/<uuid:uuid>/update/",
        TransferUpdateView.as_view(),
        name="transfer_update",
    ),
    path(
        "transfers/<uuid:uuid>/delete/",
        TransferDeleteView.as_view(),
        name="transfer_delete",
    ),
    path(
        "transfers/<uuid:uuid>/lines/",
        TransferLinesView.as_view(),
        name="transfer_lines",
    ),
    path(
        "transfers/<uuid:uuid>/reject/",
        RejectTransferView.as_view(),
        name="reject-transfer",
    ),
    path(
        "transfers/<uuid:uuid>/accept/",
        AcceptTransferView.as_view(),
        name="accept-transfer",
    ),
    path(
        "transfers/<uuid:uuid>/reverse-and-clone/",
        TransferReverseAndCloneView.as_view(),
        name="transfer-reverse-and-clone",
    ),
    path(
        "transfers/<uuid:uuid>/mark-as-draft/",
        TransferMarkAsDraftView.as_view(),
        name="transfer-mark-as-draft",
    ),
    path(
        "transfers/<uuid:uuid>/mark-as-pending/",
        TransferMarkAsPendingView.as_view(),
        name="transfer-mark-as-pending",
    ),
]
