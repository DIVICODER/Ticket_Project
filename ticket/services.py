from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from .models import Booking, Event

CENT = Decimal("0.01")
MAX_SEATS_PER_CUSTOMER = 6


def calculate_price_per_seat(event, seat_count):
    price = event.base_price
    days_left = (event.event_date - timezone.localdate()).days

    # Early bird: 30 or more days before the event -> 10% off
    if days_left >= 30:
        price = price * Decimal("0.90")

    # Group discount: 4 or more seats -> a further 5% off
    if seat_count >= 4:
        price = price * Decimal("0.95")

    return price.quantize(CENT, rounding=ROUND_HALF_UP)


def find_rejection_reason(event, email, seats):
    """Runs the booking rules in order.
    Returns the reason of the FIRST rule that fails, or None if all pass."""

    # Rule 1 (date): the event must be today or later
    if event.event_date < timezone.localdate():
        return "Event is already over."

    # Look at the CONFIRMED bookings of this event (rejected ones don't count)
    confirmed = Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED)

    taken = set()
    held_by_customer = 0
    for booking in confirmed:
        taken.update(booking.seat_list)
        if booking.customer_email.lower() == email.lower():
            held_by_customer += booking.seats

    # Rule 2 (availability): none of the seats may already be booked
    already_booked = sorted(set(seats) & taken)
    if already_booked:
        listed = ", ".join(str(s) for s in already_booked)
        return f"Seats already booked: {listed}"

    # Rule 3 (per customer): at most 6 confirmed seats per event in total
    if held_by_customer + len(seats) > MAX_SEATS_PER_CUSTOMER:
        return "Customer already holds the maximum seats for this event."

    return None


@transaction.atomic
def create_booking(event, data):
    # Lock the event so two requests can't book the same seat at the same time
    event = Event.objects.select_for_update().get(pk=event.id)
    seats = data["seat_numbers"]

    common = dict(
        event=event,
        customer_name=data["customer_name"],
        customer_email=data["customer_email"],
        seat_numbers=",".join(str(s) for s in seats),
        seats=len(seats),
    )

    reason = find_rejection_reason(event, data["customer_email"], seats)

    # A rule failed -> save as REJECTED (rejected bookings are also saved)
    if reason:
        return Booking.objects.create(
            **common,
            price_per_seat=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            status=Booking.Status.REJECTED,
            rejection_reason=reason,
        )

    # All rules passed -> save as CONFIRMED
    price = calculate_price_per_seat(event, len(seats))
    total = (price * len(seats)).quantize(CENT, rounding=ROUND_HALF_UP)
    return Booking.objects.create(
        **common,
        price_per_seat=price,
        total_amount=total,
        status=Booking.Status.CONFIRMED,
    )