-- =========================================================
-- A06 Museum Web Application
-- PostgreSQL Database Schema
-- =========================================================


-- =========================================================
-- 1. User Account
-- Stores login and account information for all users
-- =========================================================

CREATE TABLE user_account (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),

    CONSTRAINT pk_user_account
        PRIMARY KEY (user_id),

    CONSTRAINT uq_user_account_email
        UNIQUE (email)
);


-- =========================================================
-- 2. Role
-- Supports role-based access control (RBAC)
-- =========================================================

CREATE TABLE role (
    role_id INTEGER GENERATED ALWAYS AS IDENTITY,
    role_name VARCHAR(30) NOT NULL,
    description VARCHAR(255),

    CONSTRAINT pk_role
        PRIMARY KEY (role_id),

    CONSTRAINT uq_role_name
        UNIQUE (role_name)
);


-- =========================================================
-- 3. User Role
-- Connects users with their roles
-- =========================================================

CREATE TABLE user_role (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,

    CONSTRAINT pk_user_role
        PRIMARY KEY (user_id, role_id),

    CONSTRAINT fk_user_role_user
        FOREIGN KEY (user_id)
        REFERENCES user_account (user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_role_role
        FOREIGN KEY (role_id)
        REFERENCES role (role_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 4. Exhibition
-- Stores museum exhibition information
-- =========================================================

CREATE TABLE exhibition (
    exhibition_id INTEGER GENERATED ALWAYS AS IDENTITY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    location VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'Upcoming',

    CONSTRAINT pk_exhibition
        PRIMARY KEY (exhibition_id),

    CONSTRAINT ck_exhibition_dates
        CHECK (end_date >= start_date),

    CONSTRAINT ck_exhibition_status
        CHECK (status IN ('Upcoming', 'Current', 'Closed'))
);


-- =========================================================
-- 5. Collection Item
-- Stores collection items displayed by the museum
-- =========================================================

CREATE TABLE collection_item (
    item_id INTEGER GENERATED ALWAYS AS IDENTITY,
    exhibition_id INTEGER,
    item_name VARCHAR(150) NOT NULL,
    description TEXT,
    historical_period VARCHAR(100),
    is_highlight BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_collection_item
        PRIMARY KEY (item_id),

    CONSTRAINT fk_collection_item_exhibition
        FOREIGN KEY (exhibition_id)
        REFERENCES exhibition (exhibition_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 6. Museum Information
-- Stores general visitor information
-- =========================================================

CREATE TABLE museum_information (
    museum_info_id INTEGER GENERATED ALWAYS AS IDENTITY,
    museum_name VARCHAR(150) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    transport_info TEXT,
    parking_info TEXT,
    general_info TEXT,

    CONSTRAINT pk_museum_information
        PRIMARY KEY (museum_info_id)
);


-- =========================================================
-- 7. Opening Hours
-- Stores museum opening hours
-- =========================================================

CREATE TABLE opening_hours (
    opening_hours_id INTEGER GENERATED ALWAYS AS IDENTITY,
    museum_info_id INTEGER NOT NULL,
    day_of_week VARCHAR(10) NOT NULL,
    open_time TIME,
    close_time TIME,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_opening_hours
        PRIMARY KEY (opening_hours_id),

    CONSTRAINT fk_opening_hours_museum
        FOREIGN KEY (museum_info_id)
        REFERENCES museum_information (museum_info_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_opening_hours_day
        UNIQUE (museum_info_id, day_of_week),

    CONSTRAINT ck_opening_hours_day
        CHECK (
            day_of_week IN (
                'Monday',
                'Tuesday',
                'Wednesday',
                'Thursday',
                'Friday',
                'Saturday',
                'Sunday'
            )
        ),

    CONSTRAINT ck_opening_hours_time
        CHECK (
            (is_closed = TRUE AND open_time IS NULL AND close_time IS NULL)
            OR
            (is_closed = FALSE
             AND open_time IS NOT NULL
             AND close_time IS NOT NULL
             AND close_time > open_time)
        )
);


-- =========================================================
-- 8. Facility
-- Stores facilities and accessibility information
-- =========================================================

CREATE TABLE facility (
    facility_id INTEGER GENERATED ALWAYS AS IDENTITY,
    museum_info_id INTEGER NOT NULL,
    facility_name VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(100),
    accessibility_info TEXT,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT pk_facility
        PRIMARY KEY (facility_id),

    CONSTRAINT fk_facility_museum
        FOREIGN KEY (museum_info_id)
        REFERENCES museum_information (museum_info_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 9. Ticket Type
-- Stores available ticket types and prices
-- =========================================================

CREATE TABLE ticket_type (
    ticket_type_id INTEGER GENERATED ALWAYS AS IDENTITY,
    ticket_name VARCHAR(50) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,

    CONSTRAINT pk_ticket_type
        PRIMARY KEY (ticket_type_id),

    CONSTRAINT uq_ticket_type_name
        UNIQUE (ticket_name),

    CONSTRAINT ck_ticket_type_price
        CHECK (price >= 0)
);


-- =========================================================
-- 10. Ticket Reservation
-- Stores visitor ticket reservations
-- =========================================================

CREATE TABLE ticket_reservation (
    reservation_id INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER NOT NULL,
    ticket_type_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    visit_time TIME NOT NULL,
    ticket_quantity INTEGER NOT NULL,
    reservation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Reserved',

    CONSTRAINT pk_ticket_reservation
        PRIMARY KEY (reservation_id),

    CONSTRAINT fk_ticket_reservation_user
        FOREIGN KEY (user_id)
        REFERENCES user_account (user_id),

    CONSTRAINT fk_ticket_reservation_ticket_type
        FOREIGN KEY (ticket_type_id)
        REFERENCES ticket_type (ticket_type_id),

    CONSTRAINT ck_ticket_quantity
        CHECK (ticket_quantity > 0),

    CONSTRAINT ck_ticket_reservation_status
        CHECK (
            status IN ('Reserved', 'Cancelled', 'Completed')
        )
);


-- =========================================================
-- 11. Event
-- Stores museum events
-- =========================================================

CREATE TABLE event (
    event_id INTEGER GENERATED ALWAYS AS IDENTITY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    location VARCHAR(100),
    capacity INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',

    CONSTRAINT pk_event
        PRIMARY KEY (event_id),

    CONSTRAINT ck_event_time
        CHECK (end_time > start_time),

    CONSTRAINT ck_event_capacity
        CHECK (capacity > 0),

    CONSTRAINT ck_event_status
        CHECK (
            status IN ('Scheduled', 'Cancelled', 'Completed')
        )
);


-- =========================================================
-- 12. Event Registration
-- Stores visitor registrations for museum events
-- =========================================================

CREATE TABLE event_registration (
    registration_id INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Registered',

    CONSTRAINT pk_event_registration
        PRIMARY KEY (registration_id),

    CONSTRAINT fk_event_registration_user
        FOREIGN KEY (user_id)
        REFERENCES user_account (user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_event_registration_event
        FOREIGN KEY (event_id)
        REFERENCES event (event_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_event_registration
        UNIQUE (user_id, event_id),

    CONSTRAINT ck_event_registration_status
        CHECK (
            status IN ('Registered', 'Cancelled', 'Attended')
        )
);


-- =========================================================
-- 13. Membership
-- Stores membership applications and membership records
-- =========================================================

CREATE TABLE membership (
    membership_id INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER NOT NULL,
    membership_type VARCHAR(50) NOT NULL,
    application_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_date DATE,
    expiry_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',

    CONSTRAINT pk_membership
        PRIMARY KEY (membership_id),

    CONSTRAINT fk_membership_user
        FOREIGN KEY (user_id)
        REFERENCES user_account (user_id)
        ON DELETE CASCADE,

    CONSTRAINT ck_membership_status
        CHECK (
            status IN (
                'Pending',
                'Active',
                'Rejected',
                'Expired',
                'Cancelled'
            )
        ),

    CONSTRAINT ck_membership_dates
        CHECK (
            expiry_date IS NULL
            OR start_date IS NULL
            OR expiry_date >= start_date
        )
);