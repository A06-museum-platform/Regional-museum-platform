-- Admins can disable and restore accounts (docs/api-contract.md section 9,
-- PATCH /api/users/{id}). Existing accounts stay active.
ALTER TABLE user_account
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
