-- =========================================================
-- A06 Museum Web Application
-- Migration 002: media assets (staff-uploaded images/video)
-- =========================================================
-- Stores one row per uploaded file. The binary lives in
-- Supabase Storage; only the public URL is stored here.
-- Each row belongs to exactly one owner (collection item,
-- exhibition or event) enforced by the CHECK below.
-- Apply after 001_initial_schema.sql.
-- =========================================================

CREATE TABLE media_asset (
    media_id INTEGER GENERATED ALWAYS AS IDENTITY,
    collection_item_id INTEGER,
    exhibition_id INTEGER,
    event_id INTEGER,
    url TEXT NOT NULL,
    media_type VARCHAR(10) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    uploaded_by INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_media_asset
        PRIMARY KEY (media_id),

    CONSTRAINT fk_media_asset_item
        FOREIGN KEY (collection_item_id)
        REFERENCES collection_item (item_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_media_asset_exhibition
        FOREIGN KEY (exhibition_id)
        REFERENCES exhibition (exhibition_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_media_asset_event
        FOREIGN KEY (event_id)
        REFERENCES event (event_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_media_asset_uploader
        FOREIGN KEY (uploaded_by)
        REFERENCES user_account (user_id)
        ON DELETE SET NULL,

    CONSTRAINT ck_media_asset_type
        CHECK (media_type IN ('image', 'video')),

    CONSTRAINT ck_media_asset_single_owner
        CHECK (
            (collection_item_id IS NOT NULL)::integer
            + (exhibition_id IS NOT NULL)::integer
            + (event_id IS NOT NULL)::integer = 1
        )
);

CREATE INDEX ix_media_asset_item ON media_asset (collection_item_id);
CREATE INDEX ix_media_asset_exhibition ON media_asset (exhibition_id);
CREATE INDEX ix_media_asset_event ON media_asset (event_id);
