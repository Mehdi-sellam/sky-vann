from django.urls import path
from .views import *

urlpatterns = [
    # Expense URLs
    ## Expense  
    path('', ExpenseListView.as_view(), name='expense-list'),
    path('<uuid:uuid>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('create/', ExpenseCreateView.as_view(), name='expense-create'),
    path('<uuid:uuid>/update/', ExpenseUpdateView.as_view(), name='expense-update'),
    path('<uuid:uuid>/delete/', ExpenseDeleteView.as_view(), name='expense-delete'),

    ## Expense Types
    path('types/', ExpenseTypeListView.as_view(), name='expense-type-list'),
    path('types/<uuid:uuid>/', ExpenseTypeDetailView.as_view(), name='expense-type-detail'),
    path('types/create/', ExpenseTypeCreateView.as_view(), name='expense-type-create'),
    path('types/<uuid:uuid>/update/', ExpenseTypeUpdateView.as_view(), name='expense-type-update'),
    path('types/<uuid:uuid>/delete/', ExpenseTypeDeleteView.as_view(), name='expense-type-delete'),



]
