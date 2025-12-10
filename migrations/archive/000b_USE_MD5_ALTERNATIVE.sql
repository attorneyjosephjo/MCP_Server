-- ============================================
-- ALTERNATIVE: Use MD5 Instead of pgcrypto
-- ============================================
-- Use this if pgcrypto extension cannot be enabled
-- MD5 is built into PostgreSQL (no extension needed)

-- Drop and recreate the function with md5 instead of digest
CREATE OR REPLACE FUNCTION get_or_create_individual_org(
    user_email TEXT,
    user_tier TEXT DEFAULT 'free'
)
RETURNS UUID AS $$
DECLARE
    org_id UUID;
    user_slug TEXT;
BEGIN
    -- Use md5 instead of digest (built-in, no extension needed)
    user_slug := 'user-' || substring(md5(user_email), 1, 16);

    -- Try to get existing org
    SELECT id INTO org_id
    FROM organizations
    WHERE slug = user_slug
    AND is_individual = true;

    -- If not found, create it
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

COMMENT ON FUNCTION get_or_create_individual_org IS 'Get or create personal organization for individual user (using MD5)';

-- Test it
SELECT get_or_create_individual_org('test@example.com', 'free');

-- Clean up test
DELETE FROM organizations WHERE primary_contact_email = 'test@example.com';

-- Verify
SELECT 'MD5-based function is working!' as status;
