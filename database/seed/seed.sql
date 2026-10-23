-- =========================================================
-- A06 Museum Web Application -- Seed Data (PostgreSQL)
--
-- Load ONCE on a freshly migrated database (not idempotent).
-- Content is the placeholder museum used by the front end: one museum,
-- four galleries (Main Hall, Telegraph, Monster Mine, Encounter Bay).
-- Dates are relative to CURRENT_DATE, so whenever the demo database is
-- seeded it has past and upcoming events, current exhibitions and
-- future bookings.
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
-- Real bcrypt hashes from app.core.security.hash_password() so the
-- seed accounts can log in. Demo passwords (also listed in README.md):
--   alice@example.com  Visitor123!
--   ben@example.com    Member123!
--   staff@museum.org   Staff123!
--   admin@museum.org   Admin123!
-- Accounts 5-12 are extra demo visitors/members (password Visitor123!)
-- so the admin screens and event registrations have realistic numbers.
-- Demo-only credentials -- never reuse outside local development.
-- =========================================================

INSERT INTO user_account
(email, password_hash, first_name, last_name, phone)
VALUES
('alice@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Alice', 'Brown', '0400000001'),
('ben@example.com', '$2b$12$Z2igVArIb8BfJDfOpdOap.XpJF5hlnc.nAnA8yFXanKMDLpLU/kJS', 'Ben', 'Wilson', '0400000002'),
('staff@museum.org', '$2b$12$GLnBK/K/TTYGJl1EDaxhmOM8KDM80K8uNhlbAY8UrVSL7niNASWi.', 'Emma', 'Taylor', '0400000003'),
('admin@museum.org', '$2b$12$TYa4vQYE9A6z.4uXlwn4GOvFx/TBUx85aA6oXKbTetNbQHSjbQQju', 'James', 'Anderson', '0400000004'),
('priya.sharma@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Priya', 'Sharma', '0400000005'),
('tom.nguyen@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Tom', 'Nguyen', '0400000006'),
('grace.oconnor@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Grace', 'O''Connor', '0400000007'),
('liam.papadopoulos@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Liam', 'Papadopoulos', '0400000008'),
('mei.chen@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Mei', 'Chen', '0400000009'),
('jack.robertson@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Jack', 'Robertson', '0400000010'),
('sofia.rossi@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Sofia', 'Rossi', '0400000011'),
('noah.williams@example.com', '$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG', 'Noah', 'Williams', '0400000012');


-- =========================================================
-- 3. User Roles (every account is a Visitor; members also hold Member)
-- =========================================================

INSERT INTO user_role (user_id, role_id)
VALUES
(1, 1),   -- Alice: Visitor (membership application pending)
(2, 1),   -- Ben: Visitor
(2, 2),   -- Ben: Member
(3, 3),   -- Emma: Staff
(4, 4),   -- James: Admin
(5, 1), (5, 2),   -- Priya: Member (Family)
(6, 1), (6, 2),   -- Tom: Member (Individual)
(7, 1),           -- Grace: Visitor (membership expired)
(8, 1),           -- Liam: Visitor (application pending)
(9, 1), (9, 2),   -- Mei: Member (Patron)
(10, 1),          -- Jack: Visitor
(11, 1),          -- Sofia: Visitor
(12, 1);          -- Noah: Visitor


-- =========================================================
-- 4. Museum Information
-- =========================================================

INSERT INTO museum_information
(museum_name, address, phone, email, transport_info, parking_info, general_info)
VALUES
(
    'SARHN Regional Heritage Museum',
    'Adelaide Cultural Boulevard, North Terrace, Adelaide SA 5000',
    '08 8000 0000',
    'visit@sarhn.org.au',
    'Tram: Art Gallery / University stop, 40 m to the main entrance. Buses along North Terrace stop outside.',
    'Wilson Adelaide Central car park on Frome Street, flat-rate entry. Two accessible bays at the North Terrace entrance.',
    'The South Australian Regional Heritage Network museum tells the story of copper, telegraph and coastal communities across four galleries: the Main Hall, the Telegraph Gallery, the Monster Mine Gallery and the Encounter Bay Gallery. Most visits take two hours; families with children aged 10 to 14 are especially welcome.'
);


-- =========================================================
-- 5. Opening Hours (weekly pattern; staff change it seasonally)
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
-- 6. Facilities and accessibility
-- =========================================================

INSERT INTO facility
(museum_info_id, facility_name, description, location, accessibility_info, is_available)
VALUES
(1, 'Step-free access', 'Ramps and lifts reach every gallery; pram ramps throughout.', 'Main entrance, North Terrace', 'Wheelchairs can be borrowed at the front desk.', TRUE),
(1, 'Hearing loop', 'Induction loop at the front desk and in the Main Hall theatre.', 'Front desk, Main Hall', 'Switch hearing aids to the T setting.', TRUE),
(1, 'Sensory backpacks', 'Noise-reducing headphones, fidget tools and a quiet-route map.', 'Front desk', 'Free to borrow; ask when you arrive or request one when booking.', TRUE),
(1, 'Accessible toilets and parents room', 'Accessible toilets on every floor and a parents room with change table.', 'Ground floor, next to the cafe', 'Adult change table available.', TRUE),
(1, 'Cafe', 'Drinks, lunches and a kids menu.', 'Ground floor', 'Step-free; high chairs available.', TRUE),
(1, 'Cloakroom', 'Free bag and pram storage.', 'Main entrance', 'Large bags and backpacks must be left here.', TRUE);


-- =========================================================
-- 7. Exhibitions
-- status (Upcoming / Current / Closed) follows the dates; publish_status
-- is what staff control (draft exhibitions are hidden from visitors).
-- =========================================================

INSERT INTO exhibition
(title, slug, summary, description, gallery, start_date, end_date, location, status, age_min, age_max, publish_status)
VALUES
('Colonial Mining & the Overland Telegraph', 'colonial-mining-overland-telegraph', 'How copper out of the mid-north paid for the line that connected Adelaide to the world.', 'In 1872 South Australia completed one of the great engineering feats of the century, linking Adelaide across 3,200 kilometres of arid desert to Darwin and the global telegraph network. This exhibition follows the copper, the capital and the people who made it possible.', 'telegraph', CURRENT_DATE - 236, CURRENT_DATE + 23, 'Telegraph Gallery', 'Current', 10, NULL, 'published'),
('Working the Monster Mine', 'working-the-monster-mine', 'Cornish miners, Welsh smelters and the town that grew around the largest copper mine in the colony.', 'Wage ledgers, tools and photographs from six decades of work at Burra. The exhibition follows a single shift underground, from the change house to the pumping engine that kept the workings dry.', 'monster_mine', CURRENT_DATE - 251, NULL, 'Monster Mine Gallery', 'Current', NULL, NULL, 'published'),
('Whaling and the Southern Coast', 'whaling-and-the-southern-coast', 'The shore stations of Encounter Bay, and what happened when the whales stopped coming.', 'Between 1837 and the 1890s shore-based whaling was among the colony’s first export industries. This exhibition sets the economics beside the ecology, and does not flinch from either.', 'encounter_bay', CURRENT_DATE - 174, CURRENT_DATE + 128, 'Encounter Bay Gallery', 'Current', 12, NULL, 'published'),
('Kaurna Living Waters and Seasonal Calendars', 'kaurna-living-waters', 'Developed with Kaurna community members. Seasonal knowledge along the Karrawirra Parri.', 'Freshwater ecosystems, seasonal harvest cycles and language, presented under cultural authority and reviewed with the Kaurna community before display.', 'main_hall', CURRENT_DATE - 144, NULL, 'Main Hall', 'Current', NULL, NULL, 'published'),
('Narrow Gauge: the lines that moved the mid-north', 'narrow-gauge-mid-north', 'Draft. Rolling stock, timetables and the closure of the branch lines.', 'Draft listing held back while the loan agreement for the locomotive plate is finalised.', 'main_hall', CURRENT_DATE + 84, NULL, 'Main Hall', 'Upcoming', NULL, NULL, 'draft');


-- =========================================================
-- 8. Collection Items
-- =========================================================

INSERT INTO collection_item
(exhibition_id, item_name, slug, accession_number, description, historical_period, category, gallery,
 materials, year_from, year_to, is_family_friendly, is_highlight, publish_status)
VALUES
(1, 'Malachite matrix, Burra', 'malachite-matrix-burra', 'MIN-41D', 'A block of green copper carbonate cut from the Monster Mine in the 1840s. The green is what miners followed underground — where the rock turned this colour, copper was close.', 'c. 1848', 'mineral', 'monster_mine', 'Copper carbonate, quartz', 1845, 1850, TRUE, TRUE, 'published'),
(1, 'Copper relay key, Overland Telegraph', 'copper-relay-key-overland-telegraph', 'INS-1872-8', 'A hand-worked brass and copper signalling key from a repeater station on the Adelaide to Darwin line. Operators worked twelve-hour shifts relaying messages one character at a time.', '1872', 'instrument', 'telegraph', 'Brass, copper, cedar', 1872, 1872, TRUE, TRUE, 'published'),
(2, 'Redruth smelter wage ledger', 'redruth-smelter-wage-ledger', 'DOC-1851-02', 'Weekly wages recorded for smelter hands, including the Cornish surnames that still appear across the mid-north today.', '1851', 'document', 'monster_mine', 'Ink on rag paper, leather binding', 1851, 1851, FALSE, FALSE, 'published'),
(3, 'Whaling crew at Encounter Bay', 'whaling-crew-encounter-bay', 'PHO-1889-17', 'Twelve men and a beached whaleboat, photographed at the end of a season. The station closed within a decade as stocks collapsed.', '1889', 'photograph', 'encounter_bay', 'Albumen print', 1889, 1889, FALSE, TRUE, 'published'),
(2, 'Cornish beam engine flywheel segment', 'cornish-beam-engine-flywheel-segment', 'MAC-1858-01', 'One cast section of a flywheel that drove the pumps keeping the Monster Mine workings dry. The full wheel weighed over nine tonnes.', '1858', 'machinery', 'monster_mine', 'Cast iron', 1858, 1858, TRUE, FALSE, 'published'),
(1, 'Azurite nodule, Moonta', 'azurite-nodule-moonta', 'MIN-77A', 'Deep blue copper ore from the Yorke Peninsula. Azurite and malachite form together, which is why miners treated blue rock as a promising sign.', 'c. 1865', 'mineral', 'monster_mine', 'Azurite, limonite', 1860, 1870, TRUE, TRUE, 'published'),
(1, 'Morse sounder and resonator box', 'morse-sounder-resonator-box', 'INS-1901-3', 'Operators learned to read Morse by ear from the click of this sounder. The wooden box amplifies it enough to hear across a busy office.', '1901', 'instrument', 'telegraph', 'Brass, iron, jarrah', 1901, 1901, TRUE, FALSE, 'published'),
(1, 'Overland Telegraph survey field book', 'overland-telegraph-survey-field-book', 'DOC-1872-44', 'Pencil notes, water sources and daily distances recorded by a survey party working north of the Peake.', '1872', 'document', 'telegraph', 'Graphite on paper', 1871, 1872, FALSE, FALSE, 'published'),
(NULL, 'Narrow gauge locomotive builder plate', 'narrow-gauge-locomotive-builder-plate', 'MAC-1912-06', 'Cast plate from a locomotive that hauled ore and wheat on the mid-north lines until the 1960s.', '1912', 'machinery', 'main_hall', 'Brass', 1912, 1912, TRUE, FALSE, 'published'),
(2, 'Schoolchildren at the Burra open cut', 'schoolchildren-burra-open-cut', 'PHO-1931-02', 'A class excursion photographed on the rim of the open cut, seventy years after mining began.', '1931', 'photograph', 'monster_mine', 'Gelatin silver print', 1931, 1931, TRUE, FALSE, 'published'),
(3, 'Ship''s chronometer, Victor Harbor', 'ships-chronometer-victor-harbor', 'INS-1895-9', 'Used to fix longitude at sea. Losing or gaining a few seconds a day put a ship miles off course by the end of a voyage.', '1895', 'instrument', 'encounter_bay', 'Brass, mahogany, glass', 1895, 1895, TRUE, FALSE, 'published'),
(NULL, 'Kaurna language word list', 'kaurna-language-word-list', 'DOC-1866-11', 'A handwritten list compiled on the Adelaide Plains. Held and interpreted in consultation with Kaurna community members.', '1866', 'document', 'main_hall', 'Ink on paper', 1866, 1866, FALSE, FALSE, 'published'),
(NULL, 'Whim winding drum, unattributed', 'whim-winding-drum-unattributed', 'MAC-1924-03', 'Draft record. Provenance unconfirmed — the donor file gives two different mine sites and the curatorial team has not resolved which is correct.', 'c. 1924', 'machinery', 'monster_mine', 'Iron, jarrah', 1920, 1930, FALSE, FALSE, 'draft');


-- =========================================================
-- 9. Ticket Types (general admission; prices in dollars)
-- =========================================================

INSERT INTO ticket_type
(ticket_name, description, price)
VALUES
('Adult', 'Standard adult admission ticket.', 15.00),
('Concession', 'Seniors, students and concession card holders.', 10.00),
('Child', 'Ages 4 to 15. Under 4s are free and need no ticket.', 7.50),
('Member', 'Free entry for everyone covered by an active membership.', 0.00);


-- =========================================================
-- 10. Events (museum-local date and times)
-- status: Draft (hidden) / Scheduled (published) / Cancelled / Completed
-- =========================================================

INSERT INTO event
(title, slug, description, gallery, event_date, start_time, end_time, location, capacity, price, member_price,
 age_min, age_max, status)
VALUES
('Junior Field Detective: decoding the telegraph', 'junior-field-detective-telegraph', 'Young investigators decrypt real 1872 Morse transmissions, operate copper sounders and test rock samples to solve a 150-year-old missing courier mystery.', 'telegraph', CURRENT_DATE - 26, '10:30', '12:30', 'Telegraph Gallery', 20, 15.00, 0.00, 10, 14, 'Scheduled'),
('Night at the Monster Mine: lantern tour', 'night-at-the-monster-mine', 'Walk the perimeter of the open cut by candle-replica lantern. Miners’ superstitions, Cornish folklore, and what the dark actually sounded like underground.', 'monster_mine', CURRENT_DATE - 20, '19:30', '21:00', 'Monster Mine Gallery', 30, 22.00, 18.00, 12, NULL, 'Scheduled'),
('Cornish steam engine mechanics for teens', 'cornish-steam-engine-mechanics', 'Work alongside heritage steam conservators. Calculate piston compression, assemble authentic components, and find out why the pumps never stopped.', 'monster_mine', CURRENT_DATE - 12, '14:00', '16:00', 'Monster Mine Gallery', 16, 18.00, 0.00, 12, 16, 'Scheduled'),
('Kaurna weaving and ethnobotany walk', 'kaurna-weaving-ethnobotany-walk', 'Guided by Kaurna cultural educators. Explore river red gum ecosystems, harvest native sedge plants, and practise a fundamental spiral coil.', 'main_hall', CURRENT_DATE + 3, '10:00', '12:00', 'Main Hall', 24, 10.00, 0.00, NULL, NULL, 'Scheduled'),
('Curator''s cabinet: behind the specimen store', 'curators-cabinet-specimen-store', 'Members only. Senior curators open the climate-controlled subterranean vaults and bring out uncatalogued mineral collections.', 'monster_mine', CURRENT_DATE + 6, '18:00', '19:30', 'Monster Mine Gallery', 12, 0.00, 0.00, 18, NULL, 'Scheduled'),
('Fleurieu whaling and rigging: young helmsman knotcraft', 'fleurieu-whaling-rigging-knotcraft', 'Master eight square-rigging knots, decode marine signal flags, and test block-and-tackle physics on a working replica.', 'encounter_bay', CURRENT_DATE + 9, '11:00', '13:00', 'Encounter Bay Gallery', 18, 12.00, 0.00, 8, 14, 'Scheduled'),
('Reading the wage ledger: family history workshop', 'reading-the-wage-ledger', 'Bring a surname. Learn to read nineteenth-century mining payroll records and trace Cornish families through the mid-north.', 'monster_mine', CURRENT_DATE + 16, '13:00', '15:30', 'Monster Mine Gallery', 20, 15.00, 10.00, 16, NULL, 'Scheduled'),
('Narrow gauge in miniature: build and run', 'narrow-gauge-in-miniature', 'Assemble a working model wagon, then run it on the gallery test track. Take the wagon home at the end of the session.', 'main_hall', CURRENT_DATE + 23, '10:00', '12:00', 'Main Hall', 15, 20.00, 15.00, 10, 14, 'Scheduled'),
('Chronometers, longitude and the southern run', 'chronometers-longitude-southern-run', 'A curatorial lecture on how a few seconds a day put a ship miles off course, and what that meant for the whalers working out of Encounter Bay.', 'encounter_bay', CURRENT_DATE + 30, '18:30', '20:00', 'Encounter Bay Gallery', 60, 12.00, 0.00, 16, NULL, 'Scheduled'),
('Morse code and galvanic batteries: hands-on lab', 'morse-code-galvanic-batteries', 'Build a working single-cell battery, wire a sounder, and send your first message down thirty metres of line.', 'telegraph', CURRENT_DATE + 37, '10:30', '12:00', 'Telegraph Gallery', 20, 15.00, 0.00, 10, 14, 'Scheduled'),
('Summer twilight: telegraph under the stars', 'summer-twilight-telegraph', 'Draft listing. Evening session pairing the Morse lab with an outdoor astronomy talk. Dates not yet confirmed with the education team.', 'telegraph', CURRENT_DATE + 51, '19:00', '21:00', 'Telegraph Gallery', 40, 18.00, 0.00, 10, NULL, 'Draft');


-- =========================================================
-- 11. Event Registrations (parties of 1-4 from the demo accounts)
-- =========================================================

INSERT INTO event_registration
(user_id, event_id, party_size, contact_name, contact_email, registration_reference, status, registration_date)
VALUES
(5, 1, 4, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20001', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(6, 1, 3, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20002', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(7, 1, 2, 'Grace O''Connor', 'grace.oconnor@example.com', 'SARHN-EV-20003', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(8, 1, 1, 'Liam Papadopoulos', 'liam.papadopoulos@example.com', 'SARHN-EV-20004', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(9, 1, 3, 'Mei Chen', 'mei.chen@example.com', 'SARHN-EV-20005', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(10, 1, 1, 'Jack Robertson', 'jack.robertson@example.com', 'SARHN-EV-20006', 'Registered', (CURRENT_DATE - 33)::timestamp + time '10:00'),
(2, 2, 4, 'Ben Wilson', 'ben@example.com', 'SARHN-EV-20007', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(1, 2, 3, 'Alice Brown', 'alice@example.com', 'SARHN-EV-20008', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(12, 2, 2, 'Noah Williams', 'noah.williams@example.com', 'SARHN-EV-20009', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(11, 2, 1, 'Sofia Rossi', 'sofia.rossi@example.com', 'SARHN-EV-20010', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(10, 2, 3, 'Jack Robertson', 'jack.robertson@example.com', 'SARHN-EV-20011', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(9, 2, 4, 'Mei Chen', 'mei.chen@example.com', 'SARHN-EV-20012', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(8, 2, 2, 'Liam Papadopoulos', 'liam.papadopoulos@example.com', 'SARHN-EV-20013', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(7, 2, 2, 'Grace O''Connor', 'grace.oconnor@example.com', 'SARHN-EV-20014', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(6, 2, 3, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20015', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(5, 2, 3, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20016', 'Registered', (CURRENT_DATE - 27)::timestamp + time '10:00'),
(5, 3, 4, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20017', 'Registered', (CURRENT_DATE - 19)::timestamp + time '10:00'),
(6, 3, 2, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20018', 'Registered', (CURRENT_DATE - 19)::timestamp + time '10:00'),
(1, 4, 4, 'Alice Brown', 'alice@example.com', 'SARHN-EV-20019', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(12, 4, 3, 'Noah Williams', 'noah.williams@example.com', 'SARHN-EV-20020', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(11, 4, 2, 'Sofia Rossi', 'sofia.rossi@example.com', 'SARHN-EV-20021', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(5, 5, 4, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20022', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(6, 5, 3, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20023', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(7, 5, 2, 'Grace O''Connor', 'grace.oconnor@example.com', 'SARHN-EV-20024', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(8, 5, 1, 'Liam Papadopoulos', 'liam.papadopoulos@example.com', 'SARHN-EV-20025', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(9, 5, 2, 'Mei Chen', 'mei.chen@example.com', 'SARHN-EV-20026', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(1, 6, 4, 'Alice Brown', 'alice@example.com', 'SARHN-EV-20027', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(5, 7, 4, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20028', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(6, 7, 3, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20029', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(7, 7, 2, 'Grace O''Connor', 'grace.oconnor@example.com', 'SARHN-EV-20030', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(8, 7, 1, 'Liam Papadopoulos', 'liam.papadopoulos@example.com', 'SARHN-EV-20031', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(9, 7, 1, 'Mei Chen', 'mei.chen@example.com', 'SARHN-EV-20032', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(1, 8, 2, 'Alice Brown', 'alice@example.com', 'SARHN-EV-20033', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(5, 9, 4, 'Priya Sharma', 'priya.sharma@example.com', 'SARHN-EV-20034', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(6, 9, 3, 'Tom Nguyen', 'tom.nguyen@example.com', 'SARHN-EV-20035', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(7, 9, 2, 'Grace O''Connor', 'grace.oconnor@example.com', 'SARHN-EV-20036', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(8, 9, 1, 'Liam Papadopoulos', 'liam.papadopoulos@example.com', 'SARHN-EV-20037', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(9, 9, 3, 'Mei Chen', 'mei.chen@example.com', 'SARHN-EV-20038', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(10, 9, 4, 'Jack Robertson', 'jack.robertson@example.com', 'SARHN-EV-20039', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(11, 9, 2, 'Sofia Rossi', 'sofia.rossi@example.com', 'SARHN-EV-20040', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(12, 9, 2, 'Noah Williams', 'noah.williams@example.com', 'SARHN-EV-20041', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00'),
(1, 9, 2, 'Alice Brown', 'alice@example.com', 'SARHN-EV-20042', 'Registered', (CURRENT_DATE - 7)::timestamp + time '10:00');


-- =========================================================
-- 12. Membership
-- membership_type names a plan in app/services/membership_service.py
-- (Individual / Family / Patron).
-- =========================================================

INSERT INTO membership
(user_id, membership_type, application_date, start_date, expiry_date, status, children_covered)
VALUES
(2, 'Individual', CURRENT_DATE - 114, CURRENT_DATE - 113, CURRENT_DATE - 113 + INTERVAL '1 year', 'Active', 0),
(1, 'Individual', CURRENT_DATE - 3, NULL, NULL, 'Pending', 0),
(5, 'Family', CURRENT_DATE - 200, CURRENT_DATE - 199, CURRENT_DATE - 199 + INTERVAL '1 year', 'Active', 2),
(6, 'Individual', CURRENT_DATE - 60, CURRENT_DATE - 59, CURRENT_DATE - 59 + INTERVAL '1 year', 'Active', 0),
(7, 'Family', CURRENT_DATE - 420, CURRENT_DATE - 419, CURRENT_DATE - 54, 'Expired', 3),
(8, 'Family', CURRENT_DATE - 1, NULL, NULL, 'Pending', 1),
(9, 'Patron', CURRENT_DATE - 30, CURRENT_DATE - 29, CURRENT_DATE - 29 + INTERVAL '1 year', 'Active', 2),
(10, 'Individual', CURRENT_DATE - 12, NULL, NULL, 'Rejected', 0);


-- =========================================================
-- 13. Bookings (general admission, migration 008)
-- Upcoming bookings fall on a Monday so they sit inside opening hours.
-- =========================================================

INSERT INTO booking
(booking_reference, user_id, visit_date, window_start, window_end, visitor_first_name, visitor_last_name,
 visitor_email, visitor_mobile, accessibility, status, created_at)
VALUES
('SARHN-10001', 2, (CURRENT_DATE + 3 + ((8 - EXTRACT(ISODOW FROM CURRENT_DATE + 3)::int) % 7)), '11:00', '13:00', 'Ben', 'Wilson', 'ben@example.com', '0400 000 002', '{}', 'Reserved', now() - INTERVAL '2 days'),
('SARHN-10002', 2, CURRENT_DATE - 24, '09:00', '11:00', 'Ben', 'Wilson', 'ben@example.com', NULL, '{step_free}', 'Reserved', now() - INTERVAL '30 days'),
('SARHN-10003', 1, (CURRENT_DATE + 3 + ((8 - EXTRACT(ISODOW FROM CURRENT_DATE + 3)::int) % 7)), '09:00', '11:00', 'Alice', 'Brown', 'alice@example.com', '0400 000 001', '{sensory_backpack}', 'Reserved', now() - INTERVAL '1 day'),
('SARHN-10004', 5, (CURRENT_DATE + 10 + ((8 - EXTRACT(ISODOW FROM CURRENT_DATE + 10)::int) % 7)), '13:00', '15:00', 'Priya', 'Sharma', 'priya.sharma@example.com', NULL, '{}', 'Reserved', now() - INTERVAL '3 days'),
('SARHN-10005', 11, (CURRENT_DATE + 3 + ((8 - EXTRACT(ISODOW FROM CURRENT_DATE + 3)::int) % 7)), '13:00', '15:00', 'Sofia', 'Rossi', 'sofia.rossi@example.com', NULL, '{hearing_loop}', 'Cancelled', now() - INTERVAL '4 days');

INSERT INTO ticket_reservation
(booking_id, user_id, ticket_type_id, visit_date, visit_time, ticket_quantity, unit_price, status)
SELECT b.booking_id, b.user_id, v.ticket_type_id, b.visit_date, b.window_start, v.quantity, tt.price,
       CASE WHEN b.status = 'Cancelled' THEN 'Cancelled' ELSE 'Reserved' END
FROM (VALUES
    ('SARHN-10001', 4, 1),
    ('SARHN-10001', 3, 1),
    ('SARHN-10002', 4, 1),
    ('SARHN-10003', 1, 2),
    ('SARHN-10003', 3, 2),
    ('SARHN-10004', 4, 4),
    ('SARHN-10005', 1, 1),
    ('SARHN-10005', 2, 1)
) AS v(reference, ticket_type_id, quantity)
JOIN booking b ON b.booking_reference = v.reference
JOIN ticket_type tt ON tt.ticket_type_id = v.ticket_type_id;



-- =========================================================
-- 15. Interest tags on content, and members' chosen interests
-- =========================================================

INSERT INTO exhibition_tag (exhibition_id, tag_id)
SELECT c.exhibition_id, t.tag_id
FROM (VALUES
('colonial-mining-overland-telegraph', 'mining'),
('colonial-mining-overland-telegraph', 'telegraph'),
('colonial-mining-overland-telegraph', 'science'),
('kaurna-living-waters', 'aboriginal_culture'),
('kaurna-living-waters', 'family_history'),
('narrow-gauge-mid-north', 'railways'),
('narrow-gauge-mid-north', 'science'),
('whaling-and-the-southern-coast', 'maritime'),
('whaling-and-the-southern-coast', 'family_history'),
('working-the-monster-mine', 'mining'),
('working-the-monster-mine', 'family_history'),
('working-the-monster-mine', 'science')
) AS v(slug, tag)
JOIN exhibition c ON c.slug = v.slug
JOIN interest_tag t ON t.slug = v.tag;

INSERT INTO event_tag (event_id, tag_id)
SELECT c.event_id, t.tag_id
FROM (VALUES
('chronometers-longitude-southern-run', 'maritime'),
('chronometers-longitude-southern-run', 'science'),
('cornish-steam-engine-mechanics', 'mining'),
('cornish-steam-engine-mechanics', 'science'),
('cornish-steam-engine-mechanics', 'hands_on'),
('curators-cabinet-specimen-store', 'mining'),
('curators-cabinet-specimen-store', 'science'),
('fleurieu-whaling-rigging-knotcraft', 'maritime'),
('fleurieu-whaling-rigging-knotcraft', 'hands_on'),
('junior-field-detective-telegraph', 'telegraph'),
('junior-field-detective-telegraph', 'hands_on'),
('junior-field-detective-telegraph', 'science'),
('kaurna-weaving-ethnobotany-walk', 'aboriginal_culture'),
('kaurna-weaving-ethnobotany-walk', 'hands_on'),
('morse-code-galvanic-batteries', 'telegraph'),
('morse-code-galvanic-batteries', 'science'),
('morse-code-galvanic-batteries', 'hands_on'),
('narrow-gauge-in-miniature', 'railways'),
('narrow-gauge-in-miniature', 'hands_on'),
('night-at-the-monster-mine', 'mining'),
('night-at-the-monster-mine', 'family_history'),
('reading-the-wage-ledger', 'family_history'),
('reading-the-wage-ledger', 'mining'),
('summer-twilight-telegraph', 'telegraph')
) AS v(slug, tag)
JOIN event c ON c.slug = v.slug
JOIN interest_tag t ON t.slug = v.tag;

INSERT INTO collection_item_tag (item_id, tag_id)
SELECT c.item_id, t.tag_id
FROM (VALUES
('azurite-nodule-moonta', 'mining'),
('copper-relay-key-overland-telegraph', 'telegraph'),
('copper-relay-key-overland-telegraph', 'science'),
('cornish-beam-engine-flywheel-segment', 'mining'),
('cornish-beam-engine-flywheel-segment', 'science'),
('kaurna-language-word-list', 'aboriginal_culture'),
('malachite-matrix-burra', 'mining'),
('malachite-matrix-burra', 'hands_on'),
('morse-sounder-resonator-box', 'telegraph'),
('morse-sounder-resonator-box', 'hands_on'),
('narrow-gauge-locomotive-builder-plate', 'railways'),
('overland-telegraph-survey-field-book', 'telegraph'),
('overland-telegraph-survey-field-book', 'family_history'),
('redruth-smelter-wage-ledger', 'family_history'),
('redruth-smelter-wage-ledger', 'mining'),
('schoolchildren-burra-open-cut', 'family_history'),
('schoolchildren-burra-open-cut', 'mining'),
('ships-chronometer-victor-harbor', 'maritime'),
('ships-chronometer-victor-harbor', 'science'),
('whaling-crew-encounter-bay', 'maritime'),
('whaling-crew-encounter-bay', 'family_history'),
('whim-winding-drum-unattributed', 'mining'),
('whim-winding-drum-unattributed', 'science')
) AS v(slug, tag)
JOIN collection_item c ON c.slug = v.slug
JOIN interest_tag t ON t.slug = v.tag;

-- Ben likes mining and hands-on activities; Priya (family member) telegraph
-- and the sea; Mei (patron) Aboriginal culture and family history.
INSERT INTO user_interest (user_id, tag_id)
SELECT v.user_id, t.tag_id
FROM (VALUES (2, 'mining'), (2, 'hands_on'), (5, 'telegraph'), (5, 'maritime'), (5, 'hands_on'),
             (9, 'aboriginal_culture'), (9, 'family_history')) AS v(user_id, tag)
JOIN interest_tag t ON t.slug = v.tag;


-- =========================================================
-- 16. Activity log history (migration 010)
-- What the server would have written as these records were created, so
-- the member "Recent activity" panel and the admin log aren't empty.
-- =========================================================

INSERT INTO activity_log
(created_at, actor_user_id, actor_name, actor_role, action, target, reason, reference, subject_user_id)
VALUES
(now() - INTERVAL '114 days', 2, 'Ben Wilson', 'visitor', 'member.applied', 'Individual membership', NULL, 'SA-0001', 2),
(now() - INTERVAL '113 days', 4, 'James Anderson', 'admin', 'member.approved', 'Ben Wilson — Individual (SA-0001)', NULL, 'SA-0001', 2),
(now() - INTERVAL '30 days', 2, 'Ben Wilson', 'member', 'booking.created', 'Visit — 1 ticket', NULL, 'SARHN-10002', 2),
(now() - INTERVAL '27 days', 2, 'Ben Wilson', 'member', 'event.registered', 'Night at the Monster Mine: lantern tour — 4 people', NULL, 'SARHN-EV-20007', 2),
(now() - INTERVAL '12 days', 3, 'Emma Taylor', 'staff', 'event.published', 'Morse code and galvanic batteries: hands-on lab', NULL, NULL, 3),
(now() - INTERVAL '12 days', 4, 'James Anderson', 'admin', 'member.declined', 'Jack Robertson — Individual (SA-0008)', 'Application details could not be verified', 'SA-0008', 10),
(now() - INTERVAL '9 days', 3, 'Emma Taylor', 'staff', 'opening_hours.updated', 'Weekly pattern and 0 dated exceptions', NULL, NULL, 3),
(now() - INTERVAL '6 days', 3, 'Emma Taylor', 'staff', 'collection.updated', 'Malachite matrix, Burra', NULL, NULL, 3),
(now() - INTERVAL '4 days', 11, 'Sofia Rossi', 'visitor', 'booking.cancelled', 'Visit', NULL, 'SARHN-10005', 11),
(now() - INTERVAL '3 days', 1, 'Alice Brown', 'visitor', 'member.applied', 'Individual membership', NULL, 'SA-0002', 1),
(now() - INTERVAL '2 days', 2, 'Ben Wilson', 'member', 'booking.created', 'Visit — 2 tickets', NULL, 'SARHN-10001', 2),
(now() - INTERVAL '1 day', 1, 'Alice Brown', 'visitor', 'booking.created', 'Visit — 4 tickets', NULL, 'SARHN-10003', 1);


-- =========================================================
-- 14. Media
-- No placeholder photographs: random stock images would put a beach on a
-- malachite specimen. Cards show a designed gradient per category until
-- staff upload real images on the Media page (docs/design/media-storage.md).
-- =========================================================

