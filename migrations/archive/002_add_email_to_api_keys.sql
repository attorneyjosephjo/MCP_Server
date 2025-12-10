-- Migration: Add Email and Organization to API Keys (Phase 3)
-- Description: Add email as unique identifier and organization for better user management
-- Date: 2025-12-10
-- Requires: 001_create_api_keys_tables.sql

-- ============================================
-- PHASE 3: Email-Based User Management
-- ============================================

-- Add email and organization columns
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS email TEXT,
ADD COLUMN IF NOT EXISTS organization TEXT;

-- Note: Email is NOT unique - users can have multiple keys (up to 10)
-- The trigger check_api_key_limit() enforces the maximum
-- Remove any existing unique constraint if present
DROP INDEX IF EXISTS idx_api_keys_email_unique;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_email 
    ON api_keys(email);

CREATE INDEX IF NOT EXISTS idx_api_keys_organization 
    ON api_keys(organization);

-- Add check constraint to ensure email format (basic validation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'email_format_check'
        AND conrelid = 'api_keys'::regclass
    ) THEN
        ALTER TABLE api_keys
        ADD CONSTRAINT email_format_check
            CHECK (
                email IS NULL OR
                email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
            );
    END IF;
END $$;

-- Add comments
COMMENT ON COLUMN api_keys.email IS 'User email address (unique identifier for user accounts)';
COMMENT ON COLUMN api_keys.organization IS 'Organization name (e.g., "The Jo Law Firm")';

-- ============================================
-- MIGRATION HELPER: Update Existing Keys
-- ============================================

-- For existing keys without email, you can update them manually:
-- UPDATE api_keys SET email = 'admin@example.com', organization = 'Default Org' WHERE email IS NULL;

-- Or delete old test keys if no longer needed:
-- DELETE FROM api_keys WHERE email IS NULL AND client_name LIKE 'Test%';

-- ============================================
-- KEY LIMITS PER EMAIL (Optional)
-- ============================================

-- Function to check key limit per email (max 10 keys per user)
CREATE OR REPLACE FUNCTION check_api_key_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.email IS NOT NULL THEN
        IF (SELECT COUNT(*) FROM api_keys WHERE email = NEW.email AND is_active = true) >= 10 THEN
            RAISE EXCEPTION 'Maximum 10 active API keys per email address';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce key limit on insert
DROP TRIGGER IF EXISTS trigger_check_api_key_limit ON api_keys;
CREATE TRIGGER trigger_check_api_key_limit
    BEFORE INSERT ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION check_api_key_limit();

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get all keys for a user by email
CREATE OR REPLACE FUNCTION get_keys_by_email(user_email TEXT)
RETURNS TABLE (
    id UUID,
    client_name TEXT,
    key_prefix TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    total_requests BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.id,
        k.client_name,
        k.key_prefix,
        k.is_active,
        k.created_at,
        k.expires_at,
        k.total_requests
    FROM api_keys k
    WHERE k.email = user_email
    ORDER BY k.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get usage stats by organization
CREATE OR REPLACE FUNCTION get_organization_stats(org_name TEXT)
RETURNS TABLE (
    total_keys BIGINT,
    active_keys BIGINT,
    total_requests BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_keys,
        COUNT(*) FILTER (WHERE is_active = true)::BIGINT as active_keys,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
        COUNT(DISTINCT k.email)::BIGINT as unique_users
    FROM api_keys k
    WHERE k.organization = org_name;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify migration success:
-- SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'api_keys' AND column_name IN ('email', 'organization');

-- Test helper functions:
-- SELECT * FROM get_keys_by_email('test@example.com');
-- SELECT * FROM get_organization_stats('The Jo Law Firm');

-- ============================================
-- ROLLBACK (if needed)
-- ============================================

-- To rollback this migration (WARNING: This will delete email/org data):
-- DROP TRIGGER IF EXISTS trigger_check_api_key_limit ON api_keys;
-- DROP FUNCTION IF EXISTS check_api_key_limit();
-- DROP FUNCTION IF EXISTS get_keys_by_email(TEXT);
-- DROP FUNCTION IF EXISTS get_organization_stats(TEXT);
-- ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS email_format_check;
-- DROP INDEX IF EXISTS idx_api_keys_email_unique;
-- DROP INDEX IF EXISTS idx_api_keys_email;
-- DROP INDEX IF EXISTS idx_api_keys_organization;
-- ALTER TABLE api_keys DROP COLUMN IF EXISTS email;
-- ALTER TABLE api_keys DROP COLUMN IF EXISTS organization;

COMMENT ON TABLE api_keys IS 'Phase 3: Now supports email-based user management with organization tracking';

