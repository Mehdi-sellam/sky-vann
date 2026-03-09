from django.urls import path
from .views import *

urlpatterns = [
    # Customer Payment History URLs
    path('customer/payment', CustomerPaymentListView.as_view(), name='customer-payment-list'),
    path('customer/status/', StatusListView.as_view(), name='customer-status-list'),
    path('customer/payment/<uuid:uuid>/', CustomerPaymentDetailView.as_view(), name='customer-payment-detail'),
    path('customer/payment/create/', CustomerPaymentCreateView.as_view(), name='customer-payment-create'),
    path('customer/payment/<uuid:uuid>/update/', CustomerPaymentUpdateView.as_view(), name='customer-payment-update'),
    path('customer/payment/<uuid:uuid>/delete/', CustomerPaymentDeleteView.as_view(), name='customer-payment-delete'),
    path('customer/statement/pdf/<uuid:customer_uuid>/', 
         CustomerStatementPDFView.as_view(), 
         name='customer_statement_pdf'),
]
