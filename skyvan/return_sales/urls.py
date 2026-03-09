from django.urls import path
from .views import *

urlpatterns = [
    path('return_sale_orders/', ReturnSaleOrderListView.as_view(), name='return_sale_order_list'),
    path('return_sale_orders/create/', ReturnSaleOrderCreateView.as_view(), name='return_sale_order_create'),
    path('return_sale_orders/<uuid:uuid>/', ReturnSaleOrderDetailView.as_view(), name='return_sale_order_detail'),
    path('return_sale_orders/<uuid:uuid>/update/', ReturnSaleOrderUpdateView.as_view(), name='return_sale_order_update'),
    path('return_sale_orders/<uuid:uuid>/delete/', ReturnSaleOrderDeleteView.as_view(), name='return_sale_order_delete'),
    path('return_sale_orders/<uuid:uuid>/lines/', ReturnSaleOrderLinesView.as_view(), name='return_sale_order_lines'),
    path("return_sale_orders/report/", ReturnSaleLineReportView.as_view(), name="return_sale_line_report"),
]