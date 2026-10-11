--
-- PostgreSQL database dump
--

\restrict AS1uG9aWDUBhNznwlq4yD4rzJVLw95xtazjv2Xh9qPagwgRlE5ra7q5MCuBGL72

-- Dumped from database version 17.11
-- Dumped by pg_dump version 17.11

-- Started on 2026-10-10 21:10:54

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 225 (class 1259 OID 16432)
-- Name: collection_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collection_item (
    item_id integer NOT NULL,
    exhibition_id integer,
    item_name character varying(150) NOT NULL,
    description text,
    display_location character varying(200),
    discovery_date date,
    materials character varying(200),
    origin_region character varying(200)
);


--
-- TOC entry 224 (class 1259 OID 16431)
-- Name: collection_item_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.collection_item ALTER COLUMN item_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.collection_item_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 237 (class 1259 OID 16515)
-- Name: event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event (
    event_id integer NOT NULL,
    title character varying(150) NOT NULL,
    description text,
    event_date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    location character varying(100),
    capacity integer NOT NULL,
    status character varying(20) DEFAULT 'Scheduled'::character varying NOT NULL,
    CONSTRAINT ck_event_capacity CHECK ((capacity > 0)),
    CONSTRAINT ck_event_status CHECK (((status)::text = ANY ((ARRAY['Scheduled'::character varying, 'Cancelled'::character varying, 'Completed'::character varying])::text[]))),
    CONSTRAINT ck_event_time CHECK ((end_time > start_time))
);


--
-- TOC entry 236 (class 1259 OID 16514)
-- Name: event_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.event ALTER COLUMN event_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.event_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 239 (class 1259 OID 16527)
-- Name: event_registration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_registration (
    registration_id integer NOT NULL,
    user_id integer NOT NULL,
    event_id integer NOT NULL,
    registration_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status character varying(20) DEFAULT 'Registered'::character varying NOT NULL,
    CONSTRAINT ck_event_registration_status CHECK (((status)::text = ANY ((ARRAY['Registered'::character varying, 'Cancelled'::character varying, 'Attended'::character varying])::text[])))
);


--
-- TOC entry 238 (class 1259 OID 16526)
-- Name: event_registration_registration_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.event_registration ALTER COLUMN registration_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.event_registration_registration_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 16421)
-- Name: exhibition; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exhibition (
    exhibition_id integer NOT NULL,
    title character varying(150) NOT NULL,
    description text,
    start_date date NOT NULL,
    end_date date NOT NULL,
    location character varying(100),
    status character varying(20) DEFAULT 'Upcoming'::character varying NOT NULL,
    CONSTRAINT ck_exhibition_dates CHECK ((end_date >= start_date)),
    CONSTRAINT ck_exhibition_status CHECK (((status)::text = ANY ((ARRAY['Upcoming'::character varying, 'Current'::character varying, 'Closed'::character varying])::text[])))
);


--
-- TOC entry 222 (class 1259 OID 16420)
-- Name: exhibition_exhibition_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.exhibition ALTER COLUMN exhibition_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.exhibition_exhibition_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 231 (class 1259 OID 16470)
-- Name: facility; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facility (
    facility_id integer NOT NULL,
    museum_info_id integer NOT NULL,
    facility_name character varying(100) NOT NULL,
    description text,
    location character varying(100),
    accessibility_info text,
    is_available boolean DEFAULT true NOT NULL
);


--
-- TOC entry 230 (class 1259 OID 16469)
-- Name: facility_facility_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.facility ALTER COLUMN facility_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.facility_facility_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 243 (class 1259 OID 32769)
-- Name: media_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_asset (
    media_id integer NOT NULL,
    collection_item_id integer,
    exhibition_id integer,
    event_id integer,
    url text NOT NULL,
    media_type character varying(10) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    uploaded_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    storage character varying(10) DEFAULT 'remote'::character varying NOT NULL,
    CONSTRAINT ck_media_asset_single_owner CHECK ((((((collection_item_id IS NOT NULL))::integer + ((exhibition_id IS NOT NULL))::integer) + ((event_id IS NOT NULL))::integer) = 1)),
    CONSTRAINT ck_media_asset_storage CHECK (((storage)::text = ANY ((ARRAY['supabase'::character varying, 'r2'::character varying, 'local'::character varying, 'remote'::character varying])::text[]))),
    CONSTRAINT ck_media_asset_type CHECK (((media_type)::text = ANY ((ARRAY['image'::character varying, 'video'::character varying])::text[])))
);


--
-- TOC entry 242 (class 1259 OID 32768)
-- Name: media_asset_media_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.media_asset ALTER COLUMN media_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.media_asset_media_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 241 (class 1259 OID 16548)
-- Name: membership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.membership (
    membership_id integer NOT NULL,
    user_id integer NOT NULL,
    membership_type character varying(50) NOT NULL,
    application_date date DEFAULT CURRENT_DATE NOT NULL,
    start_date date,
    expiry_date date,
    status character varying(20) DEFAULT 'Pending'::character varying NOT NULL,
    CONSTRAINT ck_membership_dates CHECK (((expiry_date IS NULL) OR (start_date IS NULL) OR (expiry_date >= start_date))),
    CONSTRAINT ck_membership_status CHECK (((status)::text = ANY ((ARRAY['Pending'::character varying, 'Active'::character varying, 'Rejected'::character varying, 'Expired'::character varying, 'Cancelled'::character varying])::text[])))
);


--
-- TOC entry 240 (class 1259 OID 16547)
-- Name: membership_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.membership ALTER COLUMN membership_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.membership_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 227 (class 1259 OID 16446)
-- Name: museum_information; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.museum_information (
    museum_info_id integer NOT NULL,
    museum_name character varying(150) NOT NULL,
    address text NOT NULL,
    phone character varying(20),
    email character varying(100),
    transport_info text,
    parking_info text,
    general_info text
);


--
-- TOC entry 226 (class 1259 OID 16445)
-- Name: museum_information_museum_info_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.museum_information ALTER COLUMN museum_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.museum_information_museum_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 229 (class 1259 OID 16454)
-- Name: opening_hours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opening_hours (
    opening_hours_id integer NOT NULL,
    museum_info_id integer NOT NULL,
    day_of_week character varying(10) NOT NULL,
    open_time time without time zone,
    close_time time without time zone,
    is_closed boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_opening_hours_day CHECK (((day_of_week)::text = ANY ((ARRAY['Monday'::character varying, 'Tuesday'::character varying, 'Wednesday'::character varying, 'Thursday'::character varying, 'Friday'::character varying, 'Saturday'::character varying, 'Sunday'::character varying])::text[]))),
    CONSTRAINT ck_opening_hours_time CHECK ((((is_closed = true) AND (open_time IS NULL) AND (close_time IS NULL)) OR ((is_closed = false) AND (open_time IS NOT NULL) AND (close_time IS NOT NULL) AND (close_time > open_time))))
);


--
-- TOC entry 228 (class 1259 OID 16453)
-- Name: opening_hours_opening_hours_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.opening_hours ALTER COLUMN opening_hours_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.opening_hours_opening_hours_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 220 (class 1259 OID 16398)
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    role_id integer NOT NULL,
    role_name character varying(30) NOT NULL,
    description character varying(255)
);


--
-- TOC entry 219 (class 1259 OID 16397)
-- Name: role_role_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.role ALTER COLUMN role_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.role_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 235 (class 1259 OID 16495)
-- Name: ticket_reservation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_reservation (
    reservation_id integer NOT NULL,
    user_id integer NOT NULL,
    ticket_type_id integer NOT NULL,
    visit_date date NOT NULL,
    visit_time time without time zone NOT NULL,
    ticket_quantity integer NOT NULL,
    reservation_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    status character varying(20) DEFAULT 'Reserved'::character varying NOT NULL,
    CONSTRAINT ck_ticket_quantity CHECK ((ticket_quantity > 0)),
    CONSTRAINT ck_ticket_reservation_status CHECK (((status)::text = ANY ((ARRAY['Reserved'::character varying, 'Cancelled'::character varying, 'Completed'::character varying])::text[])))
);


--
-- TOC entry 234 (class 1259 OID 16494)
-- Name: ticket_reservation_reservation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.ticket_reservation ALTER COLUMN reservation_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ticket_reservation_reservation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 233 (class 1259 OID 16484)
-- Name: ticket_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_type (
    ticket_type_id integer NOT NULL,
    ticket_name character varying(50) NOT NULL,
    description text,
    price numeric(10,2) NOT NULL,
    CONSTRAINT ck_ticket_type_price CHECK ((price >= (0)::numeric))
);


--
-- TOC entry 232 (class 1259 OID 16483)
-- Name: ticket_type_ticket_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.ticket_type ALTER COLUMN ticket_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.ticket_type_ticket_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 218 (class 1259 OID 16390)
-- Name: user_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_account (
    user_id integer NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(50) NOT NULL,
    last_name character varying(50) NOT NULL,
    phone character varying(20)
);


--
-- TOC entry 217 (class 1259 OID 16389)
-- Name: user_account_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.user_account ALTER COLUMN user_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.user_account_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 16405)
-- Name: user_role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_role (
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


--
-- TOC entry 5046 (class 0 OID 16432)
-- Dependencies: 225
-- Data for Name: collection_item; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.collection_item (item_id, exhibition_id, item_name, description, display_location, discovery_date, materials, origin_region) FROM stdin;
6	1	Aboriginal Painted Shield	A traditional wooden shield decorated with painted patterns reflecting Aboriginal cultural heritage.	Stories of South Australia	1905-01-01	Wood, natural pigments	South Australia
7	1	Diprotodon Fossil Bone	A fossilised bone from Diprotodon, a giant prehistoric marsupial that once inhabited Australia.	Stories of South Australia	1972-01-01	Fossilised bone	South Australia
8	1	Iron Meteorite Fragment	A metallic meteorite fragment containing iron and nickel from an extraterrestrial source.	Stories of South Australia	1965-01-01	Iron, nickel	South Australia
9	1	Ediacaran Fossil Impression	A fossil impression representing ancient soft-bodied organisms from the Ediacaran period.	Stories of South Australia	1946-01-01	Sandstone	Flinders Ranges, South Australia
10	1	Aboriginal Stone Axe	A traditional stone tool used for woodworking and everyday activities.	Stories of South Australia	1910-01-01	Stone, wood, plant fibre	South Australia
11	1	Opalised Plesiosaur Fossil	An opalised marine reptile fossil representing prehistoric life in ancient Australian seas.	Stories of South Australia	1987-01-01	Opalised fossil	Coober Pedy, South Australia
12	1	Aboriginal Wooden Boomerang	A traditional wooden boomerang used by Aboriginal communities for hunting and cultural activities.	Stories of South Australia	1900-01-01	Hardwood	South Australia
13	2	Kula Trading Necklace	A traditional shell necklace representing ceremonial exchange practices in the Pacific region.	Regional Life Through Time	1930-01-01	Shell, natural fibre	Papua New Guinea
14	2	Antarctic Expedition Sledge	A wooden transport sledge representing the equipment used during early Antarctic exploration.	Regional Life Through Time	1915-01-01	Wood, metal, rope	Antarctica
15	2	Pacific Ceremonial Mask	A traditional ceremonial mask representing cultural and spiritual practices in Pacific communities.	Regional Life Through Time	1935-01-01	Wood, natural pigments, fibre	Papua New Guinea
16	2	Ancient Egyptian Amulet	A small decorative amulet inspired by ancient Egyptian religious and protective traditions.	Regional Life Through Time	1895-01-01	Faience, ceramic	Egypt
17	2	Traditional Woven Basket	A handwoven basket traditionally used for collecting and carrying food and other materials.	Regional Life Through Time	1920-01-01	Plant fibres, natural dyes	South Australia
\.


--
-- TOC entry 5058 (class 0 OID 16515)
-- Dependencies: 237
-- Data for Name: event; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.event (event_id, title, description, event_date, start_time, end_time, location, capacity, status) FROM stdin;
1	Regional History Guided Tour	A guided tour exploring key objects and stories from the museum collection.	2026-10-10	11:00:00	12:00:00	Main Gallery	30	Scheduled
2	Heritage Photography Workshop	A workshop introducing visitors to heritage photography.	2026-10-18	13:00:00	15:00:00	Activity Room	20	Scheduled
3	Meet the Curator	An opportunity to learn about museum collections from the curator.	2026-11-05	14:00:00	15:00:00	Gallery 2	25	Scheduled
\.


--
-- TOC entry 5060 (class 0 OID 16527)
-- Dependencies: 239
-- Data for Name: event_registration; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.event_registration (registration_id, user_id, event_id, registration_date, status) FROM stdin;
1	1	1	2026-09-17 20:30:12.814065	Registered
2	2	1	2026-09-17 20:30:12.814065	Registered
3	2	2	2026-09-17 20:30:12.814065	Registered
\.


--
-- TOC entry 5044 (class 0 OID 16421)
-- Dependencies: 223
-- Data for Name: exhibition; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exhibition (exhibition_id, title, description, start_date, end_date, location, status) FROM stdin;
1	Stories of South Australia	An exhibition exploring the history and communities of South Australia.	2026-07-01	2026-12-31	Gallery 1	Current
2	Regional Life Through Time	Explore how everyday life in regional communities has changed over time.	2026-09-01	2027-02-28	Gallery 2	Current
3	Australian Heritage Photography	A photography exhibition featuring regional landscapes and historic places.	2026-11-01	2027-03-31	Gallery 3	Upcoming
\.


--
-- TOC entry 5052 (class 0 OID 16470)
-- Dependencies: 231
-- Data for Name: facility; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.facility (facility_id, museum_info_id, facility_name, description, location, accessibility_info, is_available) FROM stdin;
1	1	Visitor Parking	Parking area available for museum visitors.	Main entrance	Accessible parking spaces are available.	t
2	1	Restrooms	Public restroom facilities.	Ground Floor	Wheelchair-accessible restroom available.	t
3	1	Museum Cafe	Cafe serving drinks and light meals.	Ground Floor	Step-free access available.	t
4	1	Wheelchair Access	Step-free access to public exhibition areas.	Main entrance	Wheelchair ramp and lift available.	t
\.


--
-- TOC entry 5064 (class 0 OID 32769)
-- Dependencies: 243
-- Data for Name: media_asset; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.media_asset (media_id, collection_item_id, exhibition_id, event_id, url, media_type, sort_order, is_primary, uploaded_by, created_at, storage) FROM stdin;
2	6	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/aboriginal-painted-shield.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
3	7	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/diprotodon-fossil-bone.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
4	8	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/iron-meteorite-fragment.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
5	9	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/ediacaran-fossil-impression.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
6	10	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/aboriginal-stone-axe.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
7	11	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/opalised-plesiosaur-fossil.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
8	12	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/aboriginal-wooden-boomerang.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
9	13	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/Kula%20Trading%20Necklace.png	image	1	t	\N	2026-10-10 14:09:51.71535	remote
10	14	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/antarctic-expedition-sledge.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
11	15	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/pacific-ceremonial-mask.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
12	16	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/ancient-egyptian-amulet.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
13	17	\N	\N	https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/traditional-woven-basket.jpg	image	1	t	\N	2026-10-10 14:09:51.71535	remote
\.


--
-- TOC entry 5062 (class 0 OID 16548)
-- Dependencies: 241
-- Data for Name: membership; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.membership (membership_id, user_id, membership_type, application_date, start_date, expiry_date, status) FROM stdin;
1	2	Individual	2026-07-01	2026-07-02	2027-07-01	Active
2	1	Individual	2026-09-15	\N	\N	Pending
\.


--
-- TOC entry 5048 (class 0 OID 16446)
-- Dependencies: 227
-- Data for Name: museum_information; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.museum_information (museum_info_id, museum_name, address, phone, email, transport_info, parking_info, general_info) FROM stdin;
1	Regional Heritage Museum	100 Heritage Street, South Australia	08 8000 0000	info@museum.org	Accessible by local bus services.	Free visitor parking is available near the main entrance.	A regional museum showcasing local history and cultural heritage.
\.


--
-- TOC entry 5050 (class 0 OID 16454)
-- Dependencies: 229
-- Data for Name: opening_hours; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.opening_hours (opening_hours_id, museum_info_id, day_of_week, open_time, close_time, is_closed) FROM stdin;
1	1	Monday	09:00:00	17:00:00	f
2	1	Tuesday	09:00:00	17:00:00	f
3	1	Wednesday	09:00:00	17:00:00	f
4	1	Thursday	09:00:00	17:00:00	f
5	1	Friday	09:00:00	17:00:00	f
6	1	Saturday	10:00:00	16:00:00	f
7	1	Sunday	\N	\N	t
\.


--
-- TOC entry 5041 (class 0 OID 16398)
-- Dependencies: 220
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role (role_id, role_name, description) FROM stdin;
1	Visitor	Standard museum visitor
2	Member	Museum member
3	Staff	Museum staff member
4	Admin	System administrator
\.


--
-- TOC entry 5056 (class 0 OID 16495)
-- Dependencies: 235
-- Data for Name: ticket_reservation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ticket_reservation (reservation_id, user_id, ticket_type_id, visit_date, visit_time, ticket_quantity, reservation_date, status) FROM stdin;
1	1	1	2026-09-20	10:00:00	2	2026-09-17 20:30:12.814065	Reserved
2	2	4	2026-09-21	14:00:00	1	2026-09-17 20:30:12.814065	Reserved
\.


--
-- TOC entry 5054 (class 0 OID 16484)
-- Dependencies: 233
-- Data for Name: ticket_type; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ticket_type (ticket_type_id, ticket_name, description, price) FROM stdin;
1	Adult	Standard adult admission ticket.	15.00
2	Concession	Discounted admission for eligible concession holders.	10.00
3	Child	Admission for children.	7.50
4	Member	Admission for museum members.	0.00
\.


--
-- TOC entry 5039 (class 0 OID 16390)
-- Dependencies: 218
-- Data for Name: user_account; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_account (user_id, email, password_hash, first_name, last_name, phone) FROM stdin;
1	alice@example.com	$2b$12$GDFSxsIKPNndzuKZ5jAGsOl//CZZJDcmONdymmXtKCpQfVDZuMLEG	Alice	Brown	0400000001
2	ben@example.com	$2b$12$Z2igVArIb8BfJDfOpdOap.XpJF5hlnc.nAnA8yFXanKMDLpLU/kJS	Ben	Wilson	0400000002
3	staff@museum.org	$2b$12$GLnBK/K/TTYGJl1EDaxhmOM8KDM80K8uNhlbAY8UrVSL7niNASWi.	Emma	Taylor	0400000003
4	admin@museum.org	$2b$12$TYa4vQYE9A6z.4uXlwn4GOvFx/TBUx85aA6oXKbTetNbQHSjbQQju	James	Anderson	0400000004
\.


--
-- TOC entry 5042 (class 0 OID 16405)
-- Dependencies: 221
-- Data for Name: user_role; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_role (user_id, role_id) FROM stdin;
1	1
2	1
2	2
3	3
4	4
\.


--
-- TOC entry 5070 (class 0 OID 0)
-- Dependencies: 224
-- Name: collection_item_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.collection_item_item_id_seq', 17, true);


--
-- TOC entry 5071 (class 0 OID 0)
-- Dependencies: 236
-- Name: event_event_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.event_event_id_seq', 3, true);


--
-- TOC entry 5072 (class 0 OID 0)
-- Dependencies: 238
-- Name: event_registration_registration_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.event_registration_registration_id_seq', 3, true);


--
-- TOC entry 5073 (class 0 OID 0)
-- Dependencies: 222
-- Name: exhibition_exhibition_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exhibition_exhibition_id_seq', 3, true);


--
-- TOC entry 5074 (class 0 OID 0)
-- Dependencies: 230
-- Name: facility_facility_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.facility_facility_id_seq', 4, true);


--
-- TOC entry 5075 (class 0 OID 0)
-- Dependencies: 242
-- Name: media_asset_media_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.media_asset_media_id_seq', 13, true);


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 240
-- Name: membership_membership_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.membership_membership_id_seq', 2, true);


--
-- TOC entry 5077 (class 0 OID 0)
-- Dependencies: 226
-- Name: museum_information_museum_info_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.museum_information_museum_info_id_seq', 1, true);


--
-- TOC entry 5078 (class 0 OID 0)
-- Dependencies: 228
-- Name: opening_hours_opening_hours_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.opening_hours_opening_hours_id_seq', 7, true);


--
-- TOC entry 5079 (class 0 OID 0)
-- Dependencies: 219
-- Name: role_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.role_role_id_seq', 4, true);


--
-- TOC entry 5080 (class 0 OID 0)
-- Dependencies: 234
-- Name: ticket_reservation_reservation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ticket_reservation_reservation_id_seq', 2, true);


--
-- TOC entry 5081 (class 0 OID 0)
-- Dependencies: 232
-- Name: ticket_type_ticket_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ticket_type_ticket_type_id_seq', 4, true);


--
-- TOC entry 5082 (class 0 OID 0)
-- Dependencies: 217
-- Name: user_account_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_account_user_id_seq', 4, true);


--
-- TOC entry 4849 (class 2606 OID 16439)
-- Name: collection_item pk_collection_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_item
    ADD CONSTRAINT pk_collection_item PRIMARY KEY (item_id);


--
-- TOC entry 4865 (class 2606 OID 16525)
-- Name: event pk_event; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT pk_event PRIMARY KEY (event_id);


--
-- TOC entry 4867 (class 2606 OID 16534)
-- Name: event_registration pk_event_registration; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registration
    ADD CONSTRAINT pk_event_registration PRIMARY KEY (registration_id);


--
-- TOC entry 4847 (class 2606 OID 16430)
-- Name: exhibition pk_exhibition; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exhibition
    ADD CONSTRAINT pk_exhibition PRIMARY KEY (exhibition_id);


--
-- TOC entry 4857 (class 2606 OID 16477)
-- Name: facility pk_facility; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility
    ADD CONSTRAINT pk_facility PRIMARY KEY (facility_id);


--
-- TOC entry 4877 (class 2606 OID 32780)
-- Name: media_asset pk_media_asset; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT pk_media_asset PRIMARY KEY (media_id);


--
-- TOC entry 4871 (class 2606 OID 16556)
-- Name: membership pk_membership; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership
    ADD CONSTRAINT pk_membership PRIMARY KEY (membership_id);


--
-- TOC entry 4851 (class 2606 OID 16452)
-- Name: museum_information pk_museum_information; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.museum_information
    ADD CONSTRAINT pk_museum_information PRIMARY KEY (museum_info_id);


--
-- TOC entry 4853 (class 2606 OID 16461)
-- Name: opening_hours pk_opening_hours; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_hours
    ADD CONSTRAINT pk_opening_hours PRIMARY KEY (opening_hours_id);


--
-- TOC entry 4841 (class 2606 OID 16402)
-- Name: role pk_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT pk_role PRIMARY KEY (role_id);


--
-- TOC entry 4863 (class 2606 OID 16503)
-- Name: ticket_reservation pk_ticket_reservation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_reservation
    ADD CONSTRAINT pk_ticket_reservation PRIMARY KEY (reservation_id);


--
-- TOC entry 4859 (class 2606 OID 16491)
-- Name: ticket_type pk_ticket_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_type
    ADD CONSTRAINT pk_ticket_type PRIMARY KEY (ticket_type_id);


--
-- TOC entry 4837 (class 2606 OID 16394)
-- Name: user_account pk_user_account; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT pk_user_account PRIMARY KEY (user_id);


--
-- TOC entry 4845 (class 2606 OID 16409)
-- Name: user_role pk_user_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT pk_user_role PRIMARY KEY (user_id, role_id);


--
-- TOC entry 4869 (class 2606 OID 16536)
-- Name: event_registration uq_event_registration; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registration
    ADD CONSTRAINT uq_event_registration UNIQUE (user_id, event_id);


--
-- TOC entry 4855 (class 2606 OID 16463)
-- Name: opening_hours uq_opening_hours_day; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_hours
    ADD CONSTRAINT uq_opening_hours_day UNIQUE (museum_info_id, day_of_week);


--
-- TOC entry 4843 (class 2606 OID 16404)
-- Name: role uq_role_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT uq_role_name UNIQUE (role_name);


--
-- TOC entry 4861 (class 2606 OID 16493)
-- Name: ticket_type uq_ticket_type_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_type
    ADD CONSTRAINT uq_ticket_type_name UNIQUE (ticket_name);


--
-- TOC entry 4839 (class 2606 OID 16396)
-- Name: user_account uq_user_account_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT uq_user_account_email UNIQUE (email);


--
-- TOC entry 4872 (class 1259 OID 32803)
-- Name: ix_media_asset_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_asset_event ON public.media_asset USING btree (event_id);


--
-- TOC entry 4873 (class 1259 OID 32802)
-- Name: ix_media_asset_exhibition; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_asset_exhibition ON public.media_asset USING btree (exhibition_id);


--
-- TOC entry 4874 (class 1259 OID 32801)
-- Name: ix_media_asset_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_asset_item ON public.media_asset USING btree (collection_item_id);


--
-- TOC entry 4875 (class 1259 OID 32806)
-- Name: ix_media_asset_storage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_asset_storage ON public.media_asset USING btree (storage);


--
-- TOC entry 4880 (class 2606 OID 16440)
-- Name: collection_item fk_collection_item_exhibition; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_item
    ADD CONSTRAINT fk_collection_item_exhibition FOREIGN KEY (exhibition_id) REFERENCES public.exhibition(exhibition_id) ON DELETE SET NULL;


--
-- TOC entry 4885 (class 2606 OID 16542)
-- Name: event_registration fk_event_registration_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registration
    ADD CONSTRAINT fk_event_registration_event FOREIGN KEY (event_id) REFERENCES public.event(event_id) ON DELETE CASCADE;


--
-- TOC entry 4886 (class 2606 OID 16537)
-- Name: event_registration fk_event_registration_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_registration
    ADD CONSTRAINT fk_event_registration_user FOREIGN KEY (user_id) REFERENCES public.user_account(user_id) ON DELETE CASCADE;


--
-- TOC entry 4882 (class 2606 OID 16478)
-- Name: facility fk_facility_museum; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility
    ADD CONSTRAINT fk_facility_museum FOREIGN KEY (museum_info_id) REFERENCES public.museum_information(museum_info_id) ON DELETE CASCADE;


--
-- TOC entry 4888 (class 2606 OID 32807)
-- Name: media_asset fk_media_asset_collection_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT fk_media_asset_collection_item FOREIGN KEY (collection_item_id) REFERENCES public.collection_item(item_id);


--
-- TOC entry 4889 (class 2606 OID 32791)
-- Name: media_asset fk_media_asset_event; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT fk_media_asset_event FOREIGN KEY (event_id) REFERENCES public.event(event_id) ON DELETE CASCADE;


--
-- TOC entry 4890 (class 2606 OID 32786)
-- Name: media_asset fk_media_asset_exhibition; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT fk_media_asset_exhibition FOREIGN KEY (exhibition_id) REFERENCES public.exhibition(exhibition_id) ON DELETE CASCADE;


--
-- TOC entry 4891 (class 2606 OID 32781)
-- Name: media_asset fk_media_asset_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT fk_media_asset_item FOREIGN KEY (collection_item_id) REFERENCES public.collection_item(item_id) ON DELETE CASCADE;


--
-- TOC entry 4892 (class 2606 OID 32796)
-- Name: media_asset fk_media_asset_uploader; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_asset
    ADD CONSTRAINT fk_media_asset_uploader FOREIGN KEY (uploaded_by) REFERENCES public.user_account(user_id) ON DELETE SET NULL;


--
-- TOC entry 4887 (class 2606 OID 16557)
-- Name: membership fk_membership_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.membership
    ADD CONSTRAINT fk_membership_user FOREIGN KEY (user_id) REFERENCES public.user_account(user_id) ON DELETE CASCADE;


--
-- TOC entry 4881 (class 2606 OID 16464)
-- Name: opening_hours fk_opening_hours_museum; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_hours
    ADD CONSTRAINT fk_opening_hours_museum FOREIGN KEY (museum_info_id) REFERENCES public.museum_information(museum_info_id) ON DELETE CASCADE;


--
-- TOC entry 4883 (class 2606 OID 16509)
-- Name: ticket_reservation fk_ticket_reservation_ticket_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_reservation
    ADD CONSTRAINT fk_ticket_reservation_ticket_type FOREIGN KEY (ticket_type_id) REFERENCES public.ticket_type(ticket_type_id);


--
-- TOC entry 4884 (class 2606 OID 16504)
-- Name: ticket_reservation fk_ticket_reservation_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_reservation
    ADD CONSTRAINT fk_ticket_reservation_user FOREIGN KEY (user_id) REFERENCES public.user_account(user_id);


--
-- TOC entry 4878 (class 2606 OID 16415)
-- Name: user_role fk_user_role_role; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT fk_user_role_role FOREIGN KEY (role_id) REFERENCES public.role(role_id) ON DELETE CASCADE;


--
-- TOC entry 4879 (class 2606 OID 16410)
-- Name: user_role fk_user_role_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT fk_user_role_user FOREIGN KEY (user_id) REFERENCES public.user_account(user_id) ON DELETE CASCADE;


-- Completed on 2026-10-10 21:10:55

--
-- PostgreSQL database dump complete
--

\unrestrict AS1uG9aWDUBhNznwlq4yD4rzJVLw95xtazjv2Xh9qPagwgRlE5ra7q5MCuBGL72

