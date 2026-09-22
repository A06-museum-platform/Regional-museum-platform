-- =========================================================
-- A06 Museum Web Application
-- Migration 003: media storage backend tracking
-- =========================================================
-- Records WHICH backend holds each file so reads, deletes and
-- failover know where to go. Pre-existing rows are classified by URL
-- shape (not blanket-defaulted): real Supabase uploads keep working
-- with delete/mirror/repoint, while seed placeholders stay 'remote'
-- ("nothing to delete, nothing to mirror").
-- Apply after 002_media_assets.sql.
-- =========================================================

ALTER TABLE media_asset
    ADD COLUMN storage VARCHAR(10);

-- Backfill from URL shape. Supabase public URLs always contain
-- '/storage/v1/object/public/'; R2 URLs end in '.r2.dev/' (or a custom
-- domain recorded here at classification time); local-mode rows are
-- '/uploads/…' paths. Anything else is a third-party seed URL.
UPDATE media_asset SET storage = 'supabase'
WHERE url LIKE '%/storage/v1/object/public/%';
UPDATE media_asset SET storage = 'r2'
WHERE storage IS NULL AND url LIKE '%r2.dev/%';
UPDATE media_asset SET storage = 'local'
WHERE storage IS NULL AND url LIKE '/uploads/%';
UPDATE media_asset SET storage = 'remote'
WHERE storage IS NULL;

ALTER TABLE media_asset
    ALTER COLUMN storage SET NOT NULL;
ALTER TABLE media_asset
    ALTER COLUMN storage SET DEFAULT 'remote';

ALTER TABLE media_asset
    ADD CONSTRAINT ck_media_asset_storage
    CHECK (storage IN ('supabase', 'r2', 'local', 'remote'));

CREATE INDEX ix_media_asset_storage ON media_asset (storage);
