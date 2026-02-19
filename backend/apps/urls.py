from django.urls import path
from .views import TicketListCreateView, TicketDetailView, stats_view, classify_view

urlpatterns = [
    path("apps/", TicketListCreateView.as_view(), name="ticket-list-create"),
    path("apps/<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("apps/stats/", stats_view, name="ticket-stats"),
    path("apps/classify/", classify_view, name="ticket-classify"),
]