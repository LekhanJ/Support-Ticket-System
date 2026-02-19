import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticket
from .serializers import ClassifyRequestSerializer, TicketSerializer
from .services import classify_ticket

logger = logging.getLogger(__name__)


class TicketListCreateView(APIView):
    def get(self, request):
        queryset = Ticket.objects.all()

        category = request.query_params.get("category")
        priority = request.query_params.get("priority")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")

        if category:
            queryset = queryset.filter(category=category)
        if priority:
            queryset = queryset.filter(priority=priority)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        serializer = TicketSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save()
            return Response(
                TicketSerializer(ticket).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketDetailView(APIView):
    def get_object(self, pk):
        try:
            return Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return None

    def patch(self, request, pk):
        ticket = self.get_object(pk)
        if not ticket:
            return Response(
                {"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = TicketSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def stats_view(request):
    total = Ticket.objects.count()
    open_count = Ticket.objects.filter(status=Ticket.Status.OPEN).count()

    daily_counts = (
        Ticket.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    if daily_counts:
        total_days = daily_counts.count()
        total_sum = sum(d["count"] for d in daily_counts)
        avg_per_day = round(total_sum / total_days, 1) if total_days > 0 else 0.0
    else:
        avg_per_day = 0.0

    priority_qs = (
        Ticket.objects.values("priority").annotate(count=Count("id"))
    )
    priority_breakdown = {p.value: 0 for p in Ticket.Priority}
    for row in priority_qs:
        priority_breakdown[row["priority"]] = row["count"]

    category_qs = (
        Ticket.objects.values("category").annotate(count=Count("id"))
    )
    category_breakdown = {c.value: 0 for c in Ticket.Category}
    for row in category_qs:
        category_breakdown[row["category"]] = row["count"]

    return Response(
        {
            "total_tickets": total,
            "open_tickets": open_count,
            "avg_tickets_per_day": avg_per_day,
            "priority_breakdown": priority_breakdown,
            "category_breakdown": category_breakdown,
        }
    )


@api_view(["POST"])
def classify_view(request):
    serializer = ClassifyRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    description = serializer.validated_data["description"]
    result = classify_ticket(description)

    return Response(result, status=status.HTTP_200_OK)
