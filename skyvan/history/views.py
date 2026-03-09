from rest_framework import generics
from .models import History
from .serializers import HistorySerializer
from .filters import HistoryFilter


class HistoryList(generics.ListAPIView):
    queryset = History.objects.all()
    serializer_class = HistorySerializer
    filterset_class = HistoryFilter
