from .views import *
from django.urls import path
urlpatterns = [
    # List all warehouses
    path('',WarehouseListView.as_view(),name='warehouse_list'),
    # Create a new warehouse
    path('create/', WarehouseCreateView.as_view(), name='warehouse_create'),
    # Retrieve, update, or delete a specific warehouse by UUID
    path('<uuid:uuid>/', WarehouseDetailView.as_view(), name='warehouse_detail'), 
    # List inventory for a specific warehouse by UUID
    path('<uuid:uuid>/warehouse-inventory',WarehouseInventoryListView.as_view(),name='warehouse_inventory'),
    path('<uuid:uuid>/inventory',InventoryListView.as_view(),name='inventory'),

    # List central inventory
    path('central-inventory/', CentralInventoryView.as_view(), name='central-inventory'),
]