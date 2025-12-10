-- ============================================
-- FIX: Enable pgcrypto Extension
-- ============================================

-- Check if pgcrypto is already enabled
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

-- If the above returns no rows, enable it:
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Verify it's enabled
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

-- Test the digest function
SELECT encode(digest('test@example.com'::bytea, 'sha256'::text), 'hex') as test_hash;

-- If the above works, test the full slug generation
SELECT 'user-' || substring(
    encode(digest('test@example.com'::bytea, 'sha256'::text), 'hex'),
    1, 16
) as test_slug;

-- Test the actual function
SELECT get_or_create_individual_org('test-verify@example.com', 'free');

-- Clean up test org
DELETE FROM organizations WHERE primary_contact_email = 'test-verify@example.com';

-- ============================================
-- If you get an error about permissions:
-- ============================================

-- Option 1: Try with schema prefix
-- CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

-- Option 2: Check available extensions
-- SELECT * FROM pg_available_extensions WHERE name = 'pgcrypto';

-- Option 3: If pgcrypto is not available, use alternative hash function
-- (This is a workaround if pgcrypto cannot be enabled)
/*
CREATE OR REPLACE FUNCTION get_or_create_individual_org(
    user_email TEXT,
    user_tier TEXT DEFAULT 'free'
)
RETURNS UUID AS $$
DECLARE
    org_id UUID;
    user_slug TEXT;
BEGIN
    -- Alternative: Use md5 instead of digest (built-in, no extension needed)
    user_slug := 'user-' || substring(md5(user_email), 1, 16);

    SELECT id INTO org_id
    FROM organizations
    WHERE slug = user_slug
    AND is_individual = true;

    IF org_id IS NULL THEN
        INSERT INTO organizations (
            name,
            slug,
            tier,
            primary_contact_email,
            is_individual
        ) VALUES (
            'Personal - ' || user_email,
            user_slug,
            user_tier,
            user_email,
            true
        )
        RETURNING id INTO org_id;
    END IF;

    RETURN org_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
*/
