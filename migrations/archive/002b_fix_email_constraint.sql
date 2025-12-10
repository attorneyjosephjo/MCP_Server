-- Fix: Remove UNIQUE constraint on email
-- This allows users to have multiple API keys (up to 10 per email)
-- The trigger check_api_key_limit() enforces the maximum

-- Drop the unique index
DROP INDEX IF EXISTS idx_api_keys_email_unique;

-- Email index remains (for fast lookups, but not unique)
-- idx_api_keys_email already exists

-- Verify no unique constraint exists
-- Run this query to confirm:
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'api_keys' AND indexname LIKE '%email%';

