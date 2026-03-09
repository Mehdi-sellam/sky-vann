from django.urls import path
from .views import *

urlpatterns = [
    # Supplier Payment History URLs
    path(
        "supplier/payment",
        SupplierPaymentListView.as_view(),
        name="supplier-payment-list",
    ),
    path(
        "supplier/payment/<uuid:uuid>/",
        SupplierPaymentDetailView.as_view(),
        name="supplier-payment-detail",
    ),
    path(
        "supplier/payment/create/",
        SupplierPaymentCreateView.as_view(),
        name="supplier-payment-create",
    ),
    path(
        "supplier/payment/<uuid:uuid>/update/",
        SupplierPaymentUpdateView.as_view(),
        name="supplier-payment-update",
    ),
    path(
        "supplier/payment/<uuid:uuid>/delete/",
        SupplierPaymentDeleteView.as_view(),
        name="supplier-payment-delete",
    ),
    path(
        "supplier/statement/pdf/<uuid:supplier_uuid>/",
        SupplierStatementPDFView.as_view(),
        name="supplier_statement_pdf",
    ),
]
