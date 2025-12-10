-- Fix: Add explicit type casts to digest() function calls
-- Date: 2025-12-10
-- Fixes: "function digest(bytea, unknown) does not exist" error
-- Description: Some PostgreSQL configurations require explicit type casts for both parameters

-- NOTE: This is a quick fix that only updates the function without re-running the full migration
-- If you haven't run 005 yet, use the full migration instead

-- Drop and recreate the function with proper type casts
DROP FUNCTION IF EXISTS get_or_create_individual_org(TEXT, TEXT);

CREATE OR REPLACE FUNCTION get_or_create_individual_org(
    user_email TEXT,
    user_tier TEXT DEFAULT 'free'
)
RETURNS UUID AS $$
DECLARE
    org_id UUID;
    user_slug TEXT;
BEGIN
    -- Generate slug from email (with explicit type casts for both parameters)
    user_slug := 'user-' || substring(
        encode(digest(user_email::bytea, 'sha256'::text), 'hex'),
        1, 16
    );

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
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_or_create_individual_org IS 'Get or create a personal organization for an individual user (with explicit type casts)';

-- Verification: Test the function
DO $$
DECLARE
    test_org_id UUID;
BEGIN
    RAISE NOTICE 'Testing get_or_create_individual_org function...';

    -- Test with a sample email
    test_org_id := get_or_create_individual_org('test@example.com', 'free');

    RAISE NOTICE 'Success! Created/retrieved org: %', test_org_id;

    -- Clean up test org (optional - comment out if you want to keep it)
    DELETE FROM organizations WHERE id = test_org_id;
    RAISE NOTICE 'Cleaned up test organization';
END $$;
