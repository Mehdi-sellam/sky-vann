from django.urls import path
from .views import *

urlpatterns = [
    path('return_purchase_orders/', ReturnPurchaseOrderListView.as_view(), name='return_purchase_order_list'),
    path('return_purchase_orders/create/', CreateReturnPurchaseOrderView.as_view(), name='return_purchase_order_create'),
    path('return_purchase_orders/<uuid:uuid>/', ReturnPurchaseOrderDetailView.as_view(), name='return_purchase_order_detail'),
    path('return_purchase_orders/<uuid:uuid>/update/', UpdateReturnPurchaseOrderView.as_view(), name='return_purchase_order_update'),
    path('return_purchase_orders/<uuid:uuid>/delete/', DeleteReturnPurchaseOrderView.as_view(), name='return_purchase_order_delete'),
    path('return_purchase_orders/<uuid:uuid>/lines/', ReturnPurchaseOrderLinesView.as_view(), name='return_purchase_order_lines'),
    path("return_purchase_orders/report/", ReturnPurchaseLineReportView.as_view(), name="return-purchase-line-report"),
    
]