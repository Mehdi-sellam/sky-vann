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
        'statistics/most-sold-products/top-10/',
        MostSoldProductsTop10.as_view(),
        name="most-sold-products-top-10",
    ),
    path(
        'statistics/products-net-revenue/',
        SortedNetRevenue.as_view(),
        name="products-net-revenue",
    ),
    path(
        'statistics/products-net-revenue/top-10/',
        SortedNetRevenueTop10.as_view(),
        name="products-net-revenue-top-10",
    ),
    path(
        'statistics/products-profit/',
        SortedNetProfit.as_view(),
        name="products-profit",
    ),
    path(
        'statistics/products-profit/top-10/',
        SortedNetProfitTop10.as_view(),
        name="products-profit-top-10",
    ),
]
