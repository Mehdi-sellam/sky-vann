from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from analytics.services import calculate_profit_statistics, get_all_products_statistics, get_sorted_net_revenue_per_product, get_most_sold_products, get_sorted_products_by_profit
from account.authentication import User
from core.pagination import CustomPagination
from van.models import VanAssignment
from .serializers import (
    ProductStatisticsSerializer,
    SortedExpectedRevenueSerializer,
    MostSoldProductsSerializer,
    SortedNetProfitSerializer,
    ProfitStatisticsSerializer,
)
from datetime import datetime
from .error_codes import AnalyticsErrorCode
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class ProfitStatisticsView(APIView):
    @extend_schema(
        summary="Get Profit Statistics",
        description="Returns profit statistics, including total revenue, cost of goods sold (COGS), gross profit, net profit, and profit margin.",
        responses={200: ProfitStatisticsSerializer},
        parameters=[
            OpenApiParameter(
                name="date_before",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Start date (YYYY-MM-DD)",  # Ensuring this appears first
            ),
            OpenApiParameter(
                name="date_after",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="End date (YYYY-MM-DD)",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        date_after = request.query_params.get("date_after")
        date_before = request.query_params.get("date_before")

        try:
            if date_before:
                date_before = datetime.strptime(date_before, "%Y-%m-%d").date()
            if date_after:
                date_after = datetime.strptime(date_after, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {
                    "code": "INVALID_DATE_FORMAT",
                    "message": "Invalid date format. Use YYYY-MM-DD.",
                    "field": "date",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stats = calculate_profit_statistics(date_after, date_before)
            serializer = ProfitStatisticsSerializer(stats)
            return Response(serializer.data)
        except Exception as e:
            error_data = {
                "code": AnalyticsErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "An unexpected error occurred while calculating profit statistics.",
                "details": str(e),
            }
            return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ProductStatisticsView(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    
    @extend_schema(
        tags=['Sales Statistics'],
        operation_id="retrieveUserProductStatistics",
        summary="Get sales statistics for all products from all vans assigned to a user",
        description="Returns a list of all products with their transferred, sold, and remaining quantities for sales made from vans.",
        parameters=[
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.PATH,
                description="user UUID",
                required=True,
                type=OpenApiTypes.UUID,
            ),
            OpenApiParameter(
                name="van_uuids",
                type=str,
                location=OpenApiParameter.QUERY,
                description="van UUID",
                required=True,
            ),
            OpenApiParameter("start_date", type=str, description="YYYY-MM-DD", required=True),
            OpenApiParameter("end_date", type=str, description="YYYY-MM-DD", required=True),
            OpenApiParameter(
                name="page",
                location=OpenApiParameter.QUERY,
                description="Page number for pagination.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                location=OpenApiParameter.QUERY,
                description="Number of results per page.",
                required=False,
                type=int,
            ),
        ],
        responses={200: ProductStatisticsSerializer},

    )

    def get(self, request, uuid): 
        try:
            queryset = get_all_products_statistics(uuid, request)
            
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            
            serializer = ProductStatisticsSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        

        except ValidationError as e:
            # Returns the nice dictionary you defined in your helper functions
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except PermissionDenied as e:
            return Response({
                "code": "permission_denied",
                "message": str(e)
            }, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            return Response({
                "code": "internal_server_error",
                "message": "An unexpected error occurred while fetching statistics.",
                "details": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        


class MostSoldProducts(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    @extend_schema(
        tags=["Sales Statistics"],
        operation_id="listMostSoldProducts",
        summary="Get most sold products sorted by quantity within a dates interval",
        parameters=[
            OpenApiParameter("start_date", type=str, description="YYYY-MM-DD", required=False),
            OpenApiParameter("end_date", type=str, description="YYYY-MM-DD", required=False),
            OpenApiParameter("page", location=OpenApiParameter.QUERY, type=int, required=False),
            OpenApiParameter("page_size", location=OpenApiParameter.QUERY, type=int, required=False),
        ],
        responses={200: MostSoldProductsSerializer(many=True)},
    )
    def get(self, request):
        try:
            rows = get_most_sold_products(request)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(rows, request)
            serializer = MostSoldProductsSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValidationError as e:
            return Response(
                e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred while fetching statistics.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        


class SortedNetRevenue(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    @extend_schema(
        tags=["Sales Statistics"],
        operation_id="listProductsNetRevenue",
        summary="Get sorted statistics per product sold from a van by its revenue, get the quantity sum and calculate its the avg_unit_price",
        parameters=[
            OpenApiParameter("page", location=OpenApiParameter.QUERY, type=int, required=False),
            OpenApiParameter("page_size", location=OpenApiParameter.QUERY, type=int, required=False),
        ],
        responses={200: SortedExpectedRevenueSerializer(many=True)},
    )
    def get(self, request):
        try:
            rows = get_sorted_net_revenue_per_product()

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(rows, request)
            serializer = SortedExpectedRevenueSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred while fetching statistics.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        



class SortedNetProfit(APIView):
    # permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    @extend_schema(
        tags=["Sales Statistics"],
        operation_id="listProductsNetProfit",
        summary="Get sorted statistics per product sold from a van by its revenue, get the quantity sum and calculate its the avg_unit_price",
        parameters=[
            OpenApiParameter("page", location=OpenApiParameter.QUERY, type=int, required=False),
            OpenApiParameter("page_size", location=OpenApiParameter.QUERY, type=int, required=False),
        ],
        responses={200: SortedNetProfitSerializer(many=True)},
    )
    def get(self, request):
        try:
            rows = get_sorted_products_by_profit()

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(rows, request)
            serializer = SortedNetProfitSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred while fetching statistics.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
