-- Content fields the visitor pages and staff editors already use
-- (docs/decisions.md, 2026-10-23 "Data model enrichment").
--
-- Additive only: no existing column is renamed or dropped, so the ERD's
-- tables keep their meaning. Locked scope: one museum, four named galleries.
--
--   collection_item  slug, accession number, category, gallery, materials,
--                    year range, family-friendly flag, draft/published
--   exhibition       slug, summary, gallery, age range, draft/published;
--                    end_date becomes optional (long-term displays)
--   event            slug, gallery, prices, age range, 'Draft' status
--   event_registration  party size, contact details, reference; one active
--                    registration per account and event
--   membership       children covered (schema question 3)
--   opening_hours    a note per weekday ("Late opening")
--   opening_hours_override  dated exceptions to the weekly pattern
--                    (public holidays, special late nights)

-- Gallery and category values are the keys of GALLERIES / CATEGORIES in
-- frontend/src/api/constants.js.

-- ---------------------------------------------------------------------------
-- collection_item
-- ---------------------------------------------------------------------------
ALTER TABLE collection_item
    ADD COLUMN slug VARCHAR(80),
    ADD COLUMN accession_number VARCHAR(40),
    ADD COLUMN category VARCHAR(30),
    ADD COLUMN gallery VARCHAR(30),
    ADD COLUMN materials VARCHAR(200),
    ADD COLUMN year_from INTEGER,
    ADD COLUMN year_to INTEGER,
    ADD COLUMN is_family_friendly BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN publish_status VARCHAR(20) NOT NULL DEFAULT 'published',
    ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Existing rows get a slug the same way the API made one before this
-- migration ("<name>-<id>"), so old links keep working.
UPDATE collection_item
SET slug = trim(both '-' from left(regexp_replace(lower(item_name), '[^a-z0-9]+', '-', 'g'), 60))
           || '-' || item_id
WHERE slug IS NULL;

ALTER TABLE collection_item
    ALTER COLUMN slug SET NOT NULL,
    ADD CONSTRAINT uq_collection_item_slug UNIQUE (slug),
    ADD CONSTRAINT uq_collection_item_accession UNIQUE (accession_number),
    ADD CONSTRAINT ck_collection_item_category
        CHECK (category IS NULL OR category IN
               ('mineral', 'instrument', 'document', 'photograph', 'machinery')),
    ADD CONSTRAINT ck_collection_item_gallery
        CHECK (gallery IS NULL OR gallery IN
               ('main_hall', 'telegraph', 'monster_mine', 'encounter_bay')),
    ADD CONSTRAINT ck_collection_item_years
        CHECK (year_from IS NULL OR year_to IS NULL OR year_to >= year_from),
    ADD CONSTRAINT ck_collection_item_publish_status
        CHECK (publish_status IN ('draft', 'published'));

-- ---------------------------------------------------------------------------
-- exhibition
-- ---------------------------------------------------------------------------
ALTER TABLE exhibition
    ADD COLUMN slug VARCHAR(80),
    ADD COLUMN summary TEXT,
    ADD COLUMN gallery VARCHAR(30),
    ADD COLUMN age_min INTEGER,
    ADD COLUMN age_max INTEGER,
    ADD COLUMN publish_status VARCHAR(20) NOT NULL DEFAULT 'published',
    ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN end_date DROP NOT NULL;

UPDATE exhibition
SET slug = trim(both '-' from left(regexp_replace(lower(title), '[^a-z0-9]+', '-', 'g'), 60))
           || '-' || exhibition_id
WHERE slug IS NULL;

ALTER TABLE exhibition
    ALTER COLUMN slug SET NOT NULL,
    ADD CONSTRAINT uq_exhibition_slug UNIQUE (slug),
    ADD CONSTRAINT ck_exhibition_gallery
        CHECK (gallery IS NULL OR gallery IN
               ('main_hall', 'telegraph', 'monster_mine', 'encounter_bay')),
    ADD CONSTRAINT ck_exhibition_ages
        CHECK (age_min IS NULL OR age_max IS NULL OR age_max >= age_min),
    ADD CONSTRAINT ck_exhibition_publish_status
        CHECK (publish_status IN ('draft', 'published'));

-- ---------------------------------------------------------------------------
-- event
-- ---------------------------------------------------------------------------
ALTER TABLE event
    ADD COLUMN slug VARCHAR(80),
    ADD COLUMN gallery VARCHAR(30),
    ADD COLUMN price NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN member_price NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN age_min INTEGER,
    ADD COLUMN age_max INTEGER,
    ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

UPDATE event
SET slug = trim(both '-' from left(regexp_replace(lower(title), '[^a-z0-9]+', '-', 'g'), 60))
           || '-' || event_id
WHERE slug IS NULL;

ALTER TABLE event
    ALTER COLUMN slug SET NOT NULL,
    ADD CONSTRAINT uq_event_slug UNIQUE (slug),
    ADD CONSTRAINT ck_event_gallery
        CHECK (gallery IS NULL OR gallery IN
               ('main_hall', 'telegraph', 'monster_mine', 'encounter_bay')),
    ADD CONSTRAINT ck_event_prices
        CHECK (price >= 0 AND member_price >= 0),
    ADD CONSTRAINT ck_event_ages
        CHECK (age_min IS NULL OR age_max IS NULL OR age_max >= age_min),
    DROP CONSTRAINT ck_event_status,
    ADD CONSTRAINT ck_event_status
        CHECK (status IN ('Draft', 'Scheduled', 'Cancelled', 'Completed'));

CREATE INDEX ix_event_date ON event (event_date, start_time);

-- ---------------------------------------------------------------------------
-- event_registration
-- ---------------------------------------------------------------------------
ALTER TABLE event_registration
    ADD COLUMN party_size INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN contact_name VARCHAR(150),
    ADD COLUMN contact_email VARCHAR(255),
    ADD COLUMN registration_reference VARCHAR(20),
    ADD CONSTRAINT ck_event_registration_party CHECK (party_size BETWEEN 1 AND 10),
    ADD CONSTRAINT uq_event_registration_reference UNIQUE (registration_reference),
    -- A cancelled registration no longer blocks registering again.
    DROP CONSTRAINT uq_event_registration;

CREATE UNIQUE INDEX uq_event_registration_active
    ON event_registration (user_id, event_id) WHERE status = 'Registered';

CREATE INDEX ix_event_registration_event ON event_registration (event_id);

-- ---------------------------------------------------------------------------
-- membership
-- ---------------------------------------------------------------------------
ALTER TABLE membership
    ADD COLUMN children_covered INTEGER NOT NULL DEFAULT 0,
    ADD CONSTRAINT ck_membership_children CHECK (children_covered BETWEEN 0 AND 10);

-- ---------------------------------------------------------------------------
-- opening_hours (weekly) and opening_hours_override (dated exceptions)
-- ---------------------------------------------------------------------------
ALTER TABLE opening_hours
    ADD COLUMN note VARCHAR(200) NOT NULL DEFAULT '';

CREATE TABLE opening_hours_override (
    override_id INTEGER GENERATED ALWAYS AS IDENTITY,
    museum_info_id INTEGER NOT NULL,
    override_date DATE NOT NULL,
    open_time TIME,
    close_time TIME,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    note VARCHAR(200) NOT NULL DEFAULT '',

    CONSTRAINT pk_opening_hours_override
        PRIMARY KEY (override_id),

    CONSTRAINT fk_opening_hours_override_museum
        FOREIGN KEY (museum_info_id)
        REFERENCES museum_information (museum_info_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_opening_hours_override_date
        UNIQUE (museum_info_id, override_date),

    CONSTRAINT ck_opening_hours_override_times
        CHECK (
            (is_closed AND open_time IS NULL AND close_time IS NULL)
            OR (NOT is_closed AND open_time IS NOT NULL AND close_time IS NOT NULL
                AND close_time > open_time)
        )
);
