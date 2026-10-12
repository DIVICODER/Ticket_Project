# Ticket Booking API

A small backend service for an events company. It lets you create events (concerts, sports, tech meetups, theatre), book seats for them, and see how well each event is selling.

It is built with **Python**, **Django** and **Django REST Framework**, and it works over plain JSON, so you can test it with Postman.

---

## What can it do?

| # | What it does | Method and URL |
|---|---|---|
| 1 | Create an event | `POST /events` |
| 2 | Get one event | `GET /events/<id>` |
| 3 | Book seats | `POST /bookings` |
| 4 | Get one booking | `GET /bookings/<id>` |
| 5 | List the bookings of an event | `GET /events/<id>/bookings` (optional `?status=confirmed` or `?status=rejected`) |
| 6 | See which seats are booked and free | `GET /events/<id>/seats` |
| 7 | See a sales summary of an event | `GET /events/<id>/summary` |

---

## How to run it on your computer

You need **Python 3.10 or newer** installed.

**1. Download the project and open a terminal in the folder that contains `manage.py`.**

**2. Create a virtual environment** (a private box for this project's packages):

```
python -m venv venv
```

**3. Turn it on:**

- Windows: `venv\Scripts\activate`
- Mac / Linux: `source venv/bin/activate`

**4. Install the packages:**

```
pip install -r requirements.txt
```

**5. Create the database tables:**

```
python manage.py migrate
```

**6. Start the server:**

```
python manage.py runserver
```

The API is now running at `http://127.0.0.1:8000`.

Optional: to look at your data in a web page, run `python manage.py createsuperuser`, then open `http://127.0.0.1:8000/admin/` and log in.

---

## The two main ideas

- An **event** is a show with a fixed number of seats. Seats are numbered `1` to `total_seats`.
- A **booking** is one customer's request for some of those seats. Every request is saved, either as `CONFIRMED` (it worked) or `REJECTED` (it broke a rule, with a reason).

---

## The APIs in detail

For `POST` requests, set the body to **raw JSON** and add the header `Content-Type: application/json`. `GET` requests need no body.

### 1. Create an event: `POST /events`

```json
{
  "name": "Rock Night",
  "venue": "City Hall",
  "category": "MUSIC",
  "event_date": "2027-03-15",
  "total_seats": 100,
  "base_price": "500.00"
}
```

Rules:

- `name` and `venue`: 3 to 100 characters.
- `category`: one of `MUSIC`, `SPORTS`, `TECH`, `THEATRE`.
- `event_date`: format `YYYY-MM-DD`, and it must be in the future.
- `total_seats`: a number from 10 to 10000.
- `base_price`: more than 0.

Responses: **201** with the new event (including its `id`), **400** if something is invalid, **409** `DUPLICATE_EVENT` if an event with the same name (ignoring capital letters) and date already exists.

### 2. Get one event: `GET /events/<id>`

Returns the event in the same shape as API 1. The id must be a positive whole number.

Responses: **200**, **400** for a bad id such as `abc` or `0`, **404** if the event doesn't exist.

### 3. Book seats: `POST /bookings`

```json
{
  "event_id": 2,
  "customer_name": "Asha Kumar",
  "customer_email": "asha@example.com",
  "seat_numbers": [1, 2, 3, 4]
}
```

Rules for the request:

- `event_id`: a positive number of an existing event.
- `customer_name`: 3 to 50 characters, letters and spaces only.
- `customer_email`: a valid email address.
- `seat_numbers`: 1 to 6 seat numbers, no duplicates, none higher than the event's `total_seats`.

Responses: **201** with the booking, **400** if the request is invalid, **404** if the event doesn't exist.

**Important:** a booking that breaks a booking rule still returns **201**, but its `status` is `REJECTED` and `rejection_reason` explains why. The rules are checked in this order, and the first one that fails is reported:

1. The event must not be over.
2. None of the seats may already be booked (by a confirmed booking).
3. One customer (one email) can hold at most 6 confirmed seats per event.

Example of a confirmed booking:

```json
{
  "id": 1,
  "event_id": 2,
  "customer_name": "Asha Kumar",
  "customer_email": "asha@example.com",
  "seat_numbers": [1, 2, 3, 4],
  "seats": 4,
  "price_per_seat": "1282.50",
  "total_amount": "5130.00",
  "status": "CONFIRMED",
  "rejection_reason": null,
  "booked_on": "2026-10-12"
}
```

### 4. Get one booking: `GET /bookings/<id>`

Returns the booking in the same shape as API 3.

Responses: **200**, **400** if the id is not a number, **404** if it doesn't exist.

### 5. List the bookings of an event: `GET /events/<id>/bookings`

Returns a list of the event's bookings, newest first. An empty list `[]` is a normal **200** answer and means "no bookings match".

You can filter with `?status=confirmed` or `?status=rejected`. Any other status value gives **400**. An event that doesn't exist gives **404**.

### 6. Seat availability: `GET /events/<id>/seats`

```json
{
  "event_id": 2,
  "total_seats": 100,
  "booked_seats": [1, 2, 3, 4],
  "available_seats": [5, 6, 7, 8, 9, 10]
}
```

(The real response lists every available seat up to `total_seats`.) Only **confirmed** bookings hold seats, and both lists are in ascending order. Responses: **200**, **400** for a non-numeric id, **404** if the event doesn't exist.

### 7. Sales summary: `GET /events/<id>/summary`

```json
{
  "event_id": 2,
  "event_name": "Tech Talk",
  "total_seats": 100,
  "seats_sold": 4,
  "seats_available": 96,
  "confirmed_bookings": 1,
  "rejected_bookings": 4,
  "total_revenue": "5130.00",
  "occupancy_pct": 4.0,
  "demand_band": "low"
}
```

- `seats_sold` and `total_revenue` count **confirmed** bookings only.
- `occupancy_pct` = seats sold ÷ total seats × 100, rounded to 1 decimal.
- `demand_band`: `low` below 40%, `medium` from 40% to 75% (inclusive), `high` above 75%.
- An event with no bookings returns zeros, `demand_band: "low"`, and `seats_available` equal to `total_seats`.

Responses: **200**, **400** for a non-numeric id, **404** if the event doesn't exist.

---

## How the price is worked out

The price per seat starts at the event's `base_price`. Then two discounts can apply automatically:

- **Early bird:** 10% off if the event is 30 or more days away.
- **Group discount:** a further 5% off if you book 4 or more seats at once.

The result is rounded to 2 decimals. Example: base price 1500, event far away, 4 seats: `1500 × 0.90 × 0.95 = 1282.50` per seat, so the total is `5130.00`.

---

## What the error messages look like

Every error comes back as JSON, never as a web page.

| Situation | Status | Body |
|---|---|---|
| Invalid data | 400 | `{"error": "VALIDATION_ERROR", "details": [{"field": "name", "message": "..."}]}` |
| Empty or broken JSON | 400 | `{"error": "INVALID_REQUEST"}` |
| Something not found | 404 | `{"error": "NOT_FOUND"}` |
| Duplicate event | 409 | `{"error": "DUPLICATE_EVENT"}` |
| Unexpected server problem | 500 | `{"error": "INTERNAL_ERROR"}` |

---

## Testing with Postman: a quick tour

1. `POST /events` to create an event. Note the `id` in the response.
2. `POST /bookings` with that `id` as `event_id`. You should see `CONFIRMED`.
3. Send the same booking again. You should see `REJECTED` with "Seats already booked".
4. `GET /events/<id>/bookings`, then add `?status=confirmed` and `?status=rejected`.
5. `GET /events/<id>/seats` to see which seats are taken.
6. `GET /events/<id>/summary` to see the sales numbers.

**Tip:** the most common mistake is sending the wrong method. Use `POST` for `/events` and `/bookings`, and `GET` for everything else. A wrong method gives `405 Method Not Allowed`.

---

## Project layout

```
manage.py
mysite/            project settings and the main URL list (urls.py)
ticket/            the app
    models.py      the Event and Booking tables
    serializers.py checks incoming data and shapes the output
    services.py    the booking rules and the price calculation
    views.py       the API endpoints
    exceptions.py  turns errors into clean JSON
requirements.txt   the packages to install
```

---

## Built with

- Python
- Django 5.2
- Django REST Framework
