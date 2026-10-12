"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from ticket import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("events", views.EventView.as_view()),
    path("events/<str:event_id>", views.EventDetailView.as_view()),
    path("bookings", views.BookTicketsView.as_view()),
    path("bookings/<str:booking_id>", views.BookingDetailView.as_view()),
    path("events/<str:event_id>/bookings", views.EventBookingListView.as_view()),
    path("events/<str:event_id>/seats", views.SeatAvailabilityView.as_view()),
    path("events/<str:event_id>/summary", views.EventSummaryView.as_view()),
]

# Return JSON instead of an HTML page for unknown URLs and server errors
handler404 = "ticket.exceptions.json_404"
handler500 = "ticket.exceptions.json_500"