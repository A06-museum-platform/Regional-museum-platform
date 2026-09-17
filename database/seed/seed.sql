-- =========================================================
-- A06 Museum Web Application
-- Seed Data
-- PostgreSQL
-- =========================================================


-- =========================================================
-- 1. Roles
-- =========================================================

INSERT INTO role (role_name, description)
VALUES
('Visitor', 'Standard museum visitor'),
('Member', 'Museum member'),
('Staff', 'Museum staff member'),
('Admin', 'System administrator');


-- =========================================================
-- 2. User Accounts
-- Password hashes below are placeholder values for prototype
-- =========================================================

INSERT INTO user_account
(email, password_hash, first_name, last_name, phone)
VALUES
('alice@example.com', 'placeholder_hash_1', 'Alice', 'Brown', '0400000001'),
('ben@example.com', 'placeholder_hash_2', 'Ben', 'Wilson', '0400000002'),
('staff@museum.org', 'placeholder_hash_3', 'Emma', 'Taylor', '0400000003'),
('admin@museum.org', 'placeholder_hash_4', 'James', 'Anderson', '0400000004');


-- =========================================================
-- 3. User Roles
-- =========================================================

INSERT INTO user_role (user_id, role_id)
VALUES
(1, 1),   -- Alice: Visitor
(2, 1),   -- Ben: Visitor
(2, 2),   -- Ben: Member
(3, 3),   -- Emma: Staff
(4, 4);   -- James: Admin


-- =========================================================
-- 4. Museum Information
-- =========================================================

INSERT INTO museum_information
(museum_name, address, phone, email, transport_info, parking_info, general_info)
VALUES
(
    'Regional Heritage Museum',
    '100 Heritage Street, South Australia',
    '08 8000 0000',
    'info@museum.org',
    'Accessible by local bus services.',
    'Free visitor parking is available near the main entrance.',
    'A regional museum showcasing local history and cultural heritage.'
);


-- =========================================================
-- 5. Opening Hours
-- =========================================================

INSERT INTO opening_hours
(museum_info_id, day_of_week, open_time, close_time, is_closed)
VALUES
(1, 'Monday',    '09:00', '17:00', FALSE),
(1, 'Tuesday',   '09:00', '17:00', FALSE),
(1, 'Wednesday', '09:00', '17:00', FALSE),
(1, 'Thursday',  '09:00', '17:00', FALSE),
(1, 'Friday',    '09:00', '17:00', FALSE),
(1, 'Saturday',  '10:00', '16:00', FALSE),
(1, 'Sunday',    NULL, NULL, TRUE);


-- =========================================================
-- 6. Facilities
-- =========================================================

INSERT INTO facility
(museum_info_id, facility_name, description, location, accessibility_info, is_available)
VALUES
(
    1,
    'Visitor Parking',
    'Parking area available for museum visitors.',
    'Main entrance',
    'Accessible parking spaces are available.',
    TRUE
),
(
    1,
    'Restrooms',
    'Public restroom facilities.',
    'Ground Floor',
    'Wheelchair-accessible restroom available.',
    TRUE
),
(
    1,
    'Museum Cafe',
    'Cafe serving drinks and light meals.',
    'Ground Floor',
    'Step-free access available.',
    TRUE
),
(
    1,
    'Wheelchair Access',
    'Step-free access to public exhibition areas.',
    'Main entrance',
    'Wheelchair ramp and lift available.',
    TRUE
);


-- =========================================================
-- 7. Exhibitions
-- =========================================================

INSERT INTO exhibition
(title, description, start_date, end_date, location, status)
VALUES
(
    'Stories of South Australia',
    'An exhibition exploring the history and communities of South Australia.',
    '2026-07-01',
    '2026-12-31',
    'Gallery 1',
    'Current'
),
(
    'Regional Life Through Time',
    'Explore how everyday life in regional communities has changed over time.',
    '2026-09-01',
    '2027-02-28',
    'Gallery 2',
    'Current'
),
(
    'Australian Heritage Photography',
    'A photography exhibition featuring regional landscapes and historic places.',
    '2026-11-01',
    '2027-03-31',
    'Gallery 3',
    'Upcoming'
);


-- =========================================================
-- 8. Collection Items
-- =========================================================

INSERT INTO collection_item
(exhibition_id, item_name, description, historical_period, is_highlight)
VALUES
(
    1,
    'Historic Farming Tool',
    'A farming tool used by early regional communities.',
    '19th Century',
    TRUE
),
(
    1,
    'Settler Diary',
    'A preserved diary describing daily life in regional South Australia.',
    '19th Century',
    TRUE
),
(
    2,
    'Vintage Radio',
    'A household radio representing changing communication technology.',
    '20th Century',
    FALSE
),
(
    2,
    'Historic School Uniform',
    'A school uniform used in a regional South Australian school.',
    '20th Century',
    TRUE
),
(
    3,
    'Regional Railway Photograph',
    'A historic photograph showing a regional railway station.',
    '20th Century',
    TRUE
);


-- =========================================================
-- 9. Ticket Types
-- =========================================================

INSERT INTO ticket_type
(ticket_name, description, price)
VALUES
(
    'Adult',
    'Standard adult admission ticket.',
    15.00
),
(
    'Concession',
    'Discounted admission for eligible concession holders.',
    10.00
),
(
    'Child',
    'Admission for children.',
    7.50
),
(
    'Member',
    'Admission for museum members.',
    0.00
);


-- =========================================================
-- 10. Ticket Reservations
-- =========================================================

INSERT INTO ticket_reservation
(user_id, ticket_type_id, visit_date, visit_time, ticket_quantity, status)
VALUES
(
    1,
    1,
    '2026-09-20',
    '10:00',
    2,
    'Reserved'
),
(
    2,
    4,
    '2026-09-21',
    '14:00',
    1,
    'Reserved'
);


-- =========================================================
-- 11. Events
-- =========================================================

INSERT INTO event
(title, description, event_date, start_time, end_time, location, capacity, status)
VALUES
(
    'Regional History Guided Tour',
    'A guided tour exploring key objects and stories from the museum collection.',
    '2026-10-10',
    '11:00',
    '12:00',
    'Main Gallery',
    30,
    'Scheduled'
),
(
    'Heritage Photography Workshop',
    'A workshop introducing visitors to heritage photography.',
    '2026-10-18',
    '13:00',
    '15:00',
    'Activity Room',
    20,
    'Scheduled'
),
(
    'Meet the Curator',
    'An opportunity to learn about museum collections from the curator.',
    '2026-11-05',
    '14:00',
    '15:00',
    'Gallery 2',
    25,
    'Scheduled'
);


-- =========================================================
-- 12. Event Registrations
-- =========================================================

INSERT INTO event_registration
(user_id, event_id, status)
VALUES
(
    1,
    1,
    'Registered'
),
(
    2,
    1,
    'Registered'
),
(
    2,
    2,
    'Registered'
);


-- =========================================================
-- 13. Membership
-- =========================================================

INSERT INTO membership
(user_id, membership_type, application_date, start_date, expiry_date, status)
VALUES
(
    2,
    'Individual',
    '2026-07-01',
    '2026-07-02',
    '2027-07-01',
    'Active'
),
(
    1,
    'Individual',
    '2026-09-15',
    NULL,
    NULL,
    'Pending'
);