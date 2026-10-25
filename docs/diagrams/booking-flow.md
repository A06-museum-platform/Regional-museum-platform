# Booking flow — general admission with simulated payment

```mermaid
sequenceDiagram
    autonumber
    actor V as Visitor
    participant UI as React app
    participant API as FastAPI
    participant DB as PostgreSQL

    V->>UI: Open /book, pick a date
    UI->>API: GET /api/bookings/availability?date=…
    API->>DB: opening hours (exception or weekly) + places taken per window
    API-->>UI: windows [{start, end, places_left}]
    V->>UI: Choose window and tickets → Continue
    alt not signed in
        UI-->>V: Sign in or create an account (choice kept in sessionStorage)
    end
    V->>UI: Visitor details, accessibility needs, tick "no payment will be taken"
    UI->>API: POST /api/bookings
    API->>DB: advisory lock on (date, window)
    API->>DB: recount places, check ticket types, member limit and 10-ticket cap
    alt room in the window
        API->>DB: INSERT booking + ticket_reservation rows, commit
        API->>DB: activity_log "booking.created"
        API-->>UI: 201 {reference: "SARHN-12345", …}
        UI-->>V: Confirmation page with pass
    else window filled meanwhile
        API-->>UI: 400 INSUFFICIENT_TICKETS
        UI-->>V: "Only N places are left — choose another time"
    end
    Note over V,DB: On the day, staff open /staff/bookings and check the booking in (status Completed)
```

Rules enforced by the server (`booking_service.py`):

| Rule | Response |
|---|---|
| Payment acknowledgement ticked | 400 otherwise |
| 1–10 tickets per booking | 409 `BOOKING_LIMIT_EXCEEDED` |
| Member tickets only with an active membership, up to the people it covers | 403 / 400 |
| Window offered on that date (open day, not passed, ≤ 60 days ahead) | 400 |
| Places left ≥ tickets, checked under a per-window lock | 400 `INSUFFICIENT_TICKETS` |
| Cancel only a `reserved` booking; places return to sale | 409 otherwise |

The lock is proven by `tests/load/race_last_places.py`: 40 simultaneous
two-ticket bookings for a 60-place window produce exactly 30 bookings.
