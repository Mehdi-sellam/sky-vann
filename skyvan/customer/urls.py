from django.urls import path
from .views import *

urlpatterns = [
    path('customers/sync/', SyncCustomer.as_view(), name='sync'),
    path('customers/', CustomerListView.as_view()),
    path('customers/<uuid:uuid>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/create/', CustomerCreateView.as_view(), name='customer-create'),
    path('customers/update/<uuid:uuid>/',
         CustomerUpdateView.as_view(), name='customer-update'),
    path('customers/delete/<uuid:uuid>/',
         CustomerDeleteView.as_view(), name='customer-delete'),
    path('customers/contacts/create/<uuid:customer_uuid>/', ContactCreateView.as_view(),
         name='create_contact'),
    path('customers/contacts/<uuid:uuid>/',
         ContactDetailView.as_view(), name='retrieve_contact'),
    path('customers/contacts/', ContactsListView.as_view(), name='list_contacts'),
    path('customers/contacts/update/<uuid:uuid>/',
         ContactUpdateView.as_view(), name='update_contact'),
    path('customers/contacts/delete/<uuid:uuid>/',
         ContactDeleteView.as_view(), name='delete_contact'),
]
