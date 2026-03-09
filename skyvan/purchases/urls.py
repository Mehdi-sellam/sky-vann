from django.urls import path
from .views import *

urlpatterns = [
    path('purchases/', PurchaseOrderView.as_view(), name='purchase-order-create-list'),
    path('purchases/<uuid:uuid>', PurchaseOrderDetails.as_view(), name='purchase-order-details'),
    path('purchases/<uuid:uuid>/lines', PurchaseOrderLinesView.as_view(), name='purchase-order-lines'),
    path("purchases-lines/report/", PurchaseLineReportView.as_view(), name="purchase-line-report"),
    
]