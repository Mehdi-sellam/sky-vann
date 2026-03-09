from django.urls import path
from .views import *

urlpatterns = [
    path('suppliers/',
         SupplierListView.as_view()),
    path('suppliers/<uuid:uuid>/', SupplierDetailView.as_view(), name='Supplier-detail'),
    path('suppliers/create/', SupplierCreateView.as_view(), name='Supplier-create'),
    path('suppliers/update/<uuid:uuid>/',
         SupplierUpdateView.as_view(), name='Supplier-update'),
    path('suppliers/delete/<uuid:uuid>/',
         SupplierDeleteView.as_view(), name='Supplier-delete'),
   
]
