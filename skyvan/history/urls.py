from django.urls import path
from .views import HistoryList

urlpatterns = [
    path('list/', HistoryList.as_view(), name='history-list'),
]
