from django.urls import path
from .views import *

urlpatterns = [
    path(
        "statistics/profit/",
        ProfitStatisticsView.as_view(),
        name="profit-statistics",
    ),
    path(
        'statistics/user/<uuid:uuid>/',
        ProductStatisticsView.as_view(),
        name="product-statistics",
    ),
    path(
        'statistics/most-sold-products/',
        MostSoldProducts.as_view(),
        name="most-sold-products",
    ),
    path(
        'statistics/products-net-revenue/',
        SortedNetRevenue.as_view(),
        name="products-net-revenue",
    ),
    path(
        'statistics/products-profit/',
        SortedNetProfit.as_view(),
        name="products-profit",
    ),
]
