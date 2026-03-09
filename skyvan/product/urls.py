from django.urls import path
from .views import *

urlpatterns = [
    path('categories',
         CategoryList.as_view()),
    path('categories/<uuid:uuid>/', CategoryDetail.as_view(), name='Category-detail'),
    path('categories/create/', CategoryCreate.as_view(), name='Category-create'),
    path('categories/update/<uuid:uuid>/',
          CategoryUpdate.as_view(), name='Category-update'),
    path('categories/delete/<uuid:uuid>/',
         CategoryDelete.as_view(), name='Category-delete'),
   # products url
       path('',
         ProductList.as_view()),
             path('<uuid:uuid>/', ProductDetail.as_view(), name='Product-detail'),
    path('create/', ProductCreate.as_view(), name='Product-create'),
    path('update/<uuid:uuid>/',
          ProductUpdate.as_view(), name='Product-update'),
    path('delete/<uuid:uuid>/',
         ProductDelete.as_view(), name='Product-delete'),
     path('<uuid:uuid>/barcodes/', ProductBarcodeListView.as_view(), name='product-barcodes'),
          path('<uuid:uuid>/barcodes/update', ProductBarcodeUpdate.as_view(), name='product-barcodes-update'),
    path('sync', SyncProduct.as_view(), name='sync_product'),
    path('list',
         ProductList.as_view(), name='product_list_sync'),
]
