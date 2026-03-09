from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from decimal import Decimal
from rest_framework import serializers

PAGE_SIZE = 12


class CustomPagination(PageNumberPagination):
    page_size = PAGE_SIZE  # Number of items per page
    page_size_query_param = "page_size"
    max_page_size = 100  # Maximum allowed page size


def get_paginated_response_schema(item_serializer):
    class PaginatedResponseSerializer(serializers.Serializer):
        count = serializers.IntegerField()
        next = serializers.CharField(allow_null=True)
        previous = serializers.CharField(allow_null=True)
        results = item_serializer(many=True)

    return PaginatedResponseSerializer


class ReportPagination(CustomPagination):
    def get_paginated_response(self, data, total_quantity=None, total_price=None):
        total_quantity = Decimal(total_quantity or "0.00").quantize(Decimal("1.00"))
        total_price = Decimal(total_price or "0.00").quantize(Decimal("1.00"))
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "total_quantity": (
                    str(total_quantity) if total_quantity is not None else "0.00"
                ),
                "total_price": str(total_price) if total_price is not None else "0.00",
                "results": data,
            }
        )
