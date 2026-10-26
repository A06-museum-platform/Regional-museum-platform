-- The October snapshot omitted two original 001 collection fields even
-- though it contained media_asset. Repair that legacy baseline additively.
-- Do not infer historical text from dates or change existing museum content.
ALTER TABLE public.collection_item
    ADD COLUMN IF NOT EXISTS historical_period VARCHAR(100),
    ADD COLUMN IF NOT EXISTS is_highlight BOOLEAN NOT NULL DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'collection_item'
          AND column_name = 'historical_period' AND data_type = 'character varying'
          AND character_maximum_length = 100 AND is_nullable = 'YES'
          AND column_default IS NULL
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'collection_item'
          AND column_name = 'is_highlight' AND data_type = 'boolean'
          AND is_nullable = 'NO' AND column_default = 'false'
    ) THEN
        RAISE EXCEPTION 'Unexpected legacy collection fields; review shape before continuing';
    END IF;
END $$;
