from django.utils import timezone
from rest_framework import serializers

from .models import Booking, Event
from django.core.validators import RegexValidator


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id", "name", "venue", "category", "event_date",
            "total_seats", "base_price", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # Rule: event_date must be in the future
    def validate_event_date(self, value):
        if value <= timezone.localdate():
            raise serializers.ValidationError("event_date must be in the future.")
        return value

class BookingRequestSerializer(serializers.Serializer):
    """Checks the body of the booking request (step 1 of the behaviour)."""

    event_id = serializers.IntegerField(min_value=1)
    customer_name = serializers.CharField(
        min_length=3,
        max_length=50,
        validators=[RegexValidator(r"^[A-Za-z ]+$", "Letters and spaces only.")],
    )
    customer_email = serializers.EmailField()
    seat_numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=6,
    )

    def validate_seat_numbers(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate seat numbers are not allowed.")
        return value


class BookingSerializer(serializers.ModelSerializer):
    """Shapes the saved booking for the response."""

    event_id = serializers.IntegerField(read_only=True)
    seat_numbers = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "event_id", "customer_name", "customer_email", "seat_numbers",
            "seats", "price_per_seat", "total_amount", "status",
            "rejection_reason", "booked_on",
        ]

    def get_seat_numbers(self, obj):
        return obj.seat_list

# class SeatListField(serializers.ListField):
#     """Takes a list of numbers like [12, 13] and returns it the same way,
#     even though the database stores it as the text '12,13'."""

#     child = serializers.IntegerField(min_value=1)

#     def to_representation(self, value):
#         if isinstance(value, str):
#             value = [int(v) for v in value.split(",") if v]
#         return super().to_representation(value)


# class BookingSerializer(serializers.ModelSerializer):
#     seat_numbers = SeatListField(min_length=1, max_length=6)

#     class Meta:
#         model = Booking
#         fields = [
#             "id", "event", "customer_name", "customer_email", "seat_numbers",
#             "seats", "price_per_seat", "total_amount", "status",
#             "rejection_reason", "booked_on",
#         ]
#         # The client only sends name, email and seat_numbers.
#         # Everything else is set by the server.
#         read_only_fields = [
#             "id", "event", "seats", "price_per_seat", "total_amount",
#             "status", "rejection_reason", "booked_on",
#         ]

#     # Rules: no duplicates, and each seat between 1 and the event's total_seats
#     def validate_seat_numbers(self, value):
#         event = self.context["event"]
#         errors = []

#         if len(value) != len(set(value)):
#             errors.append("Duplicate seat numbers are not allowed.")

#         bad = [s for s in value if s > event.total_seats]
#         if bad:
#             errors.append(
#                 f"Seat numbers must be between 1 and {event.total_seats}. Invalid: {bad}"
#             )

#         if errors:
#             raise serializers.ValidationError(errors)
#         return value