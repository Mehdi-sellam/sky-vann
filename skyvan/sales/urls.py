from django.urls import path
from .views import (
    SaleOrderListView,
    SaleOrderCreateView,
    SaleOrderDetailView,
    SaleOrderUpdateView,
    SaleOrderDeleteView,
    SaleOrderLinesView,
    SaleLineReportView,
    VanSaleOrderCreateView,
    VanSaleOrderUpdateView,
    VanSaleOrderDeleteView,
    MySaleOrderListView
)

urlpatterns = [
    path("sales/", SaleOrderListView.as_view(), name="sale_order_list"),

    path("sales/create/", SaleOrderCreateView.as_view(), name="sale_order_create"),
    path("sales/<uuid:uuid>/", SaleOrderDetailView.as_view(), name="sale_order_detail"),
    path("sales/<uuid:uuid>/update/", SaleOrderUpdateView.as_view(), name="sale_order_update"),
    path("sales/<uuid:uuid>/delete/", SaleOrderDeleteView.as_view(), name="sale_order_delete"),
    path("sales/<uuid:uuid>/lines/", SaleOrderLinesView.as_view(), name="sale_order_lines"),
    path("sale-lines/report/", SaleLineReportView.as_view(), name="sale-line-report"),
    
    # Van Sales URLs
    path("sales/my/", MySaleOrderListView.as_view(), name="my_sale_order_list"),
    path("sales/create/van/", VanSaleOrderCreateView.as_view(), name="van_sale_order_create"),
    path("sales/<uuid:uuid>/update/van/", VanSaleOrderUpdateView.as_view(),name="van_sale_order_update"),
    path("sales/<uuid:uuid>/delete/van/", VanSaleOrderDeleteView.as_view(), name="van_sale_order_delete"),

]
