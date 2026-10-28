"""Render one reviewed migration for atomic psql execution.

The October snapshot already has the exact materials column introduced by
009. Keep merged migration files immutable and validate that one known overlap.
"""

import argparse
from pathlib import Path
import re

LOCK_ID = 747104606


def render(path: Path, policy: str = "") -> str:
    name = path.name
    if not re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.sql", name):
        raise ValueError("Unexpected migration filename")
    body = path.read_text()
    compatibility = ""
    if name == "009_content_enrichment.sql":
        addition = "ADD COLUMN materials VARCHAR(200),"
        if body.count(addition) != 1:
            raise ValueError("Migration 009 compatibility mapping needs review")
        compatibility = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'collection_item'
      AND column_name = 'materials')
  AND NOT EXISTS (SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'collection_item'
      AND column_name = 'materials' AND data_type = 'character varying'
      AND character_maximum_length = 200 AND is_nullable = 'YES'
      AND column_default IS NULL) THEN
    RAISE EXCEPTION 'Existing collection_item.materials is incompatible with migration 009';
  END IF;
END $$;
"""
        body = body.replace(addition, "ADD COLUMN IF NOT EXISTS materials VARCHAR(200),")
    return rf"""SET LOCAL search_path TO public;
SELECT pg_advisory_xact_lock({LOCK_ID});
SELECT EXISTS (SELECT 1 FROM public.schema_migrations
  WHERE filename = '{name}') AS already_applied \gset
\if :already_applied
\echo skip {name} (already applied)
\else
{compatibility}
{body}
{policy}
INSERT INTO public.schema_migrations (filename) VALUES ('{name}');
\endif
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("migration", type=Path)
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    print(render(args.migration, args.policy.read_text() if args.policy else ""))
