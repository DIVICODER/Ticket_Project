from django.db import models

# Create your models here.
from decimal import Decimal

from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q


class Event(models.Model):
    class Category(models.TextChoices):
        MUSIC = "MUSIC", "Music"
        SPORTS = "SPORTS", "Sports"
        TECH = "TECH", "Tech"
        THEATRE = "THEATRE", "Theatre"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, validators=[MinLengthValidator(3)])
    venue = models.CharField(max_length=100, validators=[MinLengthValidator(3)])
    category = models.CharField(max_length=10, choices=Category.choices)
    event_date = models.DateField()
    total_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(10000)]
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events"
        ordering = ["event_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_seats__gte=10) & Q(total_seats__lte=10000),
                name="events_total_seats_10_to_10000",
            ),
            models.CheckConstraint(
                condition=Q(base_price__gt=0),
                name="events_base_price_gt_0",
            ),
        ]

    def __str__(self):
        return self.name

class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"

    id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, related_name="bookings"
    )  # stored as column "event_id"
    customer_name = models.CharField(
        max_length=50,
        validators=[
            MinLengthValidator(3),
            RegexValidator(r"^[A-Za-z ]+$", "Letters and spaces only."),
        ],
    )
    customer_email = models.EmailField()
    seat_numbers = models.CharField(max_length=50)  # "12,13,14"
    seats = models.PositiveSmallIntegerField()  # set by server
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2)  # set by server
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)  # set by server
    status = models.CharField(max_length=10, choices=Status.choices)  # set by server
    rejection_reason = models.CharField(max_length=255, null=True, blank=True)
    booked_on = models.DateField(auto_now_add=True)  # set by server

    class Meta:
        db_table = "bookings"
        ordering = ["-booked_on", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(seats__gte=1) & Q(seats__lte=6),
                name="bookings_seats_1_to_6",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="CONFIRMED", rejection_reason__isnull=True)
                    | Q(status="REJECTED", rejection_reason__isnull=False)
                ),
                name="bookings_reason_matches_status",
            ),
        ]

    @property
    def seat_list(self):
        return [int(s) for s in self.seat_numbers.split(",") if s]

    def __str__(self):
        return f"Booking {self.id} ({self.status})"