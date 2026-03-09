from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("customer.urls")),
    path("expenses/", include("expense.urls")),
    path("", include("supplier.urls")),
    path("history/", include("history.urls")),
    path("account/", include("account.urls")),
    path("products/", include("product.urls")),
    path("", include("purchases.urls")),
    path("", include("return_purchases.urls")),
    path("", include("sales.urls")),
    path("", include("return_sales.urls")),
    path("warehouses/", include("warehouse.urls")),
    path("", include("supplier_payment.urls")),
    path("", include("customer_payment.urls")),
    path("", include("transfer.urls")),
    path("", include("analytics.urls")),
    path("", include("organisation.urls")),
    path("", include("van.urls")),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)