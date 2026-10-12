from django.shortcuts import render, get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, Event
from .serializers import BookingRequestSerializer, BookingSerializer, EventSerializer
from .services import create_booking

from decimal import ROUND_HALF_UP, Decimal
from django.db.models import Sum

class BookTicketsView(APIView):
    def post(self, request):

        # Empty body check - must be first
        if not request.body:
            raise ParseError()

        # 1. Validate the body -> 400
        serializer = BookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2. Event must exist -> 404
        event = get_object_or_404(Event, pk=data["event_id"])

        # 3. Seat number higher than total_seats -> 400
        too_high = sorted(s for s in data["seat_numbers"] if s > event.total_seats)
        if too_high:
            raise ValidationError(
                {"seat_numbers": [f"Seat {s} does not exist for this event." for s in too_high]}
            )

        # 4. Run the booking rules, save, and return the booking
        booking = create_booking(event, data)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

class EventView(APIView):
    def post(self, request):

        # Empty body check - must be first
        if not request.body:
            raise ParseError()

        # 1. Validate every field (rules come from the model)
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)      # fails -> 400

        # 2. Duplicate check -> 409
        name = serializer.validated_data["name"]
        event_date = serializer.validated_data["event_date"]
        if Event.objects.filter(name__iexact=name, event_date=event_date).exists():
            return Response({"error": "DUPLICATE_EVENT"}, status=status.HTTP_409_CONFLICT)

        # 3. Save and return 201 with the generated id
        event = serializer.save()
        return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)

class EventDetailView(APIView):
    def get(self, request, event_id):

        # Rule: id must be a positive integer -> 400
        if not event_id.isdecimal() or int(event_id) <= 0:
            raise ValidationError({"id": ["id must be a positive integer."]})

        # Rule: id doesn't exist -> 404 (your exceptions.py turns this into NOT_FOUND)
        event = get_object_or_404(Event, pk=int(event_id))

        # Rule: success -> 200 with the event in the same shape as API 1
        return Response(EventSerializer(event).data, status=status.HTTP_200_OK)

class BookingDetailView(APIView):
    def get(self, request, booking_id):

        # Rule: id must be numeric -> 400
        if not booking_id.isdecimal():
            raise ValidationError({"id": ["id must be a number."]})

        # Rule: booking doesn't exist -> 404
        booking = get_object_or_404(Booking, pk=int(booking_id))

        # Rule: success -> 200 with the booking in the same shape as API 3
        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)
    
class EventBookingListView(APIView):
    def get(self, request, event_id):

        # Rule: id must be a positive integer -> 400
        if not event_id.isdecimal() or int(event_id) <= 0:
            raise ValidationError({"id": ["id must be a positive integer."]})

        # Rule: status is optional, but if given it must be confirmed or rejected -> 400
        status_param = request.query_params.get("status")
        if status_param is not None:
            status_value = status_param.upper()
            if status_value not in Booking.Status.values:
                raise ValidationError(
                    {"status": ["status must be either confirmed or rejected."]}
                )

        # Rule: event doesn't exist -> 404
        event = get_object_or_404(Event, pk=int(event_id))

        # Rule: newest first; an empty list is a valid 200
        bookings = Booking.objects.filter(event=event).order_by("-booked_on", "-id")
        if status_param is not None:
            bookings = bookings.filter(status=status_value)

        return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_200_OK)

class SeatAvailabilityView(APIView):
    def get(self, request, event_id):

        # Rule: id must be numeric -> 400
        if not event_id.isdecimal():
            raise ValidationError({"id": ["id must be a number."]})

        # Rule: event doesn't exist -> 404
        event = get_object_or_404(Event, pk=int(event_id))

        # Booked seats come from CONFIRMED bookings only (rejected ones don't hold seats)
        booked = set()
        seat_texts = Booking.objects.filter(
            event=event, status=Booking.Status.CONFIRMED
        ).values_list("seat_numbers", flat=True)
        for text in seat_texts:
            booked.update(int(s) for s in text.split(",") if s)

        # Available = every number from 1 to total_seats that is not booked
        available = [n for n in range(1, event.total_seats + 1) if n not in booked]

        # Rule: success -> 200, both lists in ascending order
        return Response(
            {
                "event_id": event.id,
                "total_seats": event.total_seats,
                "booked_seats": sorted(booked),
                "available_seats": available,
            },
            status=status.HTTP_200_OK,
        )

class EventSummaryView(APIView):
    def get(self, request, event_id):

        # Rule: id must be numeric -> 400
        if not event_id.isdecimal():
            raise ValidationError({"id": ["id must be a number."]})

        # Rule: event doesn't exist -> 404
        event = get_object_or_404(Event, pk=int(event_id))

        bookings = Booking.objects.filter(event=event)
        confirmed = bookings.filter(status=Booking.Status.CONFIRMED)

        # seats_sold and total_revenue come from CONFIRMED bookings only
        totals = confirmed.aggregate(seats=Sum("seats"), revenue=Sum("total_amount"))
        seats_sold = totals["seats"] or 0
        total_revenue = (totals["revenue"] or Decimal("0.00")).quantize(Decimal("0.01"))

        # occupancy_pct = seats_sold / total_seats * 100, rounded to 1 decimal
        occupancy = (Decimal(seats_sold) * 100 / event.total_seats).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

        # demand band: low below 40, medium 40 to 75 inclusive, high above 75
        if seats_sold * 100 < event.total_seats * 40:
            band = "low"
        elif seats_sold * 100 <= event.total_seats * 75:
            band = "medium"
        else:
            band = "high"

        return Response(
            {
                "event_id": event.id,
                "event_name": event.name,
                "total_seats": event.total_seats,
                "seats_sold": seats_sold,
                "seats_available": event.total_seats - seats_sold,
                "confirmed_bookings": confirmed.count(),
                "rejected_bookings": bookings.filter(status=Booking.Status.REJECTED).count(),
                "total_revenue": total_revenue,
                "occupancy_pct": float(occupancy),
                "demand_band": band,
            },
            status=status.HTTP_200_OK,
        )