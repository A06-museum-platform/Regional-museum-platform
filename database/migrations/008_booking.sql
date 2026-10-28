-- General-admission bookings (docs/decisions.md, "Booking and membership",
-- schema question 1). ticket_reservation keeps one row per ticket type;
-- booking groups a visit's rows under one reference and holds what the
-- booking form collects once per visit: the arrival window, who is
-- visiting and their accessibility needs. Payment is simulated and always
-- the same, so nothing about it is stored.
-- Reservations made before this migration keep booking_id NULL.

CREATE TABLE booking (
    booking_id INTEGER GENERATED ALWAYS AS IDENTITY,
    booking_reference VARCHAR(20) NOT NULL,
    user_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    window_start TIME NOT NULL,
    window_end TIME NOT NULL,
    visitor_first_name VARCHAR(100) NOT NULL,
    visitor_last_name VARCHAR(100) NOT NULL,
    visitor_email VARCHAR(255) NOT NULL,
    visitor_mobile VARCHAR(30),
    accessibility TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'Reserved',
    -- With a time zone, unlike the older tables, so the API can send UTC.
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_booking
        PRIMARY KEY (booking_id),

    CONSTRAINT uq_booking_reference
        UNIQUE (booking_reference),

    CONSTRAINT fk_booking_user
        FOREIGN KEY (user_id)
        REFERENCES user_account (user_id),

    CONSTRAINT ck_booking_window
        CHECK (window_end > window_start),

    CONSTRAINT ck_booking_status
        CHECK (
            status IN ('Reserved', 'Cancelled', 'Completed')
        )
);

CREATE INDEX ix_booking_user ON booking (user_id);

-- Each ticket line belongs to its booking, and keeps the price paid in case
-- ticket_type prices change later.
ALTER TABLE ticket_reservation
    ADD COLUMN booking_id INTEGER,
    ADD COLUMN unit_price NUMERIC(10,2),
    ADD CONSTRAINT fk_ticket_reservation_booking
        FOREIGN KEY (booking_id)
        REFERENCES booking (booking_id)
        ON DELETE CASCADE,
    ADD CONSTRAINT ck_ticket_reservation_unit_price
        CHECK (unit_price >= 0);

CREATE INDEX ix_ticket_reservation_booking ON ticket_reservation (booking_id);

-- Availability counts the places taken on a date at every page view.
CREATE INDEX ix_ticket_reservation_visit ON ticket_reservation (visit_date, visit_time);
