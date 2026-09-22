-- =========================================================
-- A06 Museum Web Application
-- Migration 003: media storage backend tracking
-- =========================================================
-- Records WHICH backend holds each file so reads, deletes and
-- failover know where to go. Existing seed rows are remote
-- placeholder URLs (picsum) — default 'remote' is truthful and
-- means "nothing to delete, nothing to mirror".
-- Apply after 002_media_assets.sql.
-- =========================================================

ALTER TABLE media_asset
    ADD COLUMN storage VARCHAR(10) NOT NULL DEFAULT 'remote';

ALTER TABLE media_asset
    ADD CONSTRAINT ck_media_asset_storage
    CHECK (storage IN ('supabase', 'r2', 'local', 'remote'));

CREATE INDEX ix_media_asset_storage ON media_asset (storage);
