-- Migration: Split Shared "Individuals" Org into Separate Personal Organizations
-- Description: Notion-style approach - each individual gets their own hidden organization
-- Date: 2025-12-10
-- Requires: 004_organizations_and_limits.sql, 004b_fix_type_mismatch.sql

-- ============================================
-- PHASE 0: ENABLE REQUIRED EXTENSIONS
-- ============================================

-- Enable pgcrypto extension for digest() function (used for creating unique slugs)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- NOTE: Type Casting Required for digest() Function
-- Some PostgreSQL configurations require explicit type casts for both parameters
-- of the digest() function. This migration uses explicit casts throughout:
--   digest(email::bytea, 'sha256'::text)
-- If you encounter errors like "function digest(bytea, unknown) does not exist",
-- see TROUBLESHOOTING_DIGEST_FUNCTION.md or run migrations/005b_fix_digest_type_casting.sql

-- ============================================
-- PHASE 1: ADD is_individual COLUMN
-- ============================================

ALTER TABLE organizations
ADD COLUMN IF NOT EXISTS is_individual BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_organizations_is_individual ON organizations(is_individual);

COMMENT ON COLUMN organizations.is_individual IS 'True for personal orgs (hidden from UI), false for real organizations';

-- ============================================
-- PHASE 2: SPLIT SHARED "INDIVIDUALS" ORG
-- ============================================

DO $$
DECLARE
    individual_org_id UUID := '00000000-0000-0000-0000-000000000000';
    key_record RECORD;
    new_org_id UUID;
    user_slug TEXT;
BEGIN
    RAISE NOTICE 'Starting migration: Splitting shared individuals org...';

    -- For each API key in the shared "individuals" organization
    FOR key_record IN
        SELECT DISTINCT ON (email)
            id, email, client_name, tier, created_at
        FROM api_keys
        WHERE organization_id = individual_org_id
        ORDER BY email, created_at ASC
    LOOP
        RAISE NOTICE 'Processing user: %', key_record.email;

        -- Generate unique slug for this individual user
        -- Format: user-{first 16 chars of sha256 hash of email}
        user_slug := 'user-' || substring(
            encode(digest(key_record.email::bytea, 'sha256'::text), 'hex'),
            1, 16
        );

        -- Create personal organization for this individual
        INSERT INTO organizations (
            name,
            slug,
            tier,
            primary_contact_email,
            is_individual,
            created_at
        ) VALUES (
            'Personal - ' || key_record.email,  -- Hidden name
            user_slug,
            COALESCE(key_record.tier, 'free'),
            key_record.email,
            true,  -- Mark as individual
            key_record.created_at
        )
        ON CONFLICT (slug) DO UPDATE
        SET primary_contact_email = EXCLUDED.primary_contact_email
        RETURNING id INTO new_org_id;

        RAISE NOTICE '  Created personal org: % (id: %)', user_slug, new_org_id;

        -- Move ALL keys for this email to their new personal organization
        UPDATE api_keys
        SET organization_id = new_org_id
        WHERE email = key_record.email
        AND organization_id = individual_org_id;

        RAISE NOTICE '  Migrated keys for %', key_record.email;
    END LOOP;

    -- Mark the old shared "individuals" org as inactive (but keep for history)
    UPDATE organizations
    SET is_active = false,
        updated_at = NOW()
    WHERE id = individual_org_id;

    RAISE NOTICE 'Migration complete! Shared individuals org marked as inactive.';
END $$;

-- ============================================
-- PHASE 3: UPDATE VIEWS FOR is_individual
-- ============================================

-- Drop and recreate organization_summary to exclude individual orgs
DROP VIEW IF EXISTS organization_summary;
CREATE VIEW organization_summary AS
SELECT
    o.id,
    o.name,
    o.slug,
    o.tier,
    o.primary_contact_email,
    t.max_keys_per_email as keys_limit,
    COUNT(k.id) as keys_used,
    COUNT(k.id) FILTER (WHERE k.is_active = true) as active_keys,
    COUNT(DISTINCT k.email) as unique_users,
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
    t.price_monthly,
    o.created_at,
    o.is_active
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.is_individual = false  -- Exclude personal orgs (hidden from UI)
AND o.is_active = true
GROUP BY o.id, o.name, o.slug, o.tier, o.primary_contact_email, t.max_keys_per_email, t.price_monthly, o.created_at, o.is_active
ORDER BY total_requests DESC;

COMMENT ON VIEW organization_summary IS 'Real organizations only (excludes personal/individual orgs)';

-- New view: Individual users summary (for admin analytics)
CREATE OR REPLACE VIEW individual_users_summary AS
SELECT
    o.id,
    o.primary_contact_email as email,
    o.tier,
    t.max_keys_per_email as keys_limit,
    COUNT(k.id) as keys_used,
    COUNT(k.id) FILTER (WHERE k.is_active = true) as active_keys,
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
    o.created_at,
    o.is_active
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.is_individual = true  -- Only personal orgs
AND o.is_active = true
GROUP BY o.id, o.primary_contact_email, o.tier, t.max_keys_per_email, o.created_at, o.is_active
ORDER BY total_requests DESC;

COMMENT ON VIEW individual_users_summary IS 'Individual users only (personal orgs hidden from public UI)';

-- ============================================
-- PHASE 4: UPDATE HELPER FUNCTIONS
-- ============================================

-- Update list_organizations_with_usage to exclude individuals by default
DROP FUNCTION IF EXISTS list_organizations_with_usage();
CREATE OR REPLACE FUNCTION list_organizations_with_usage(
    include_individuals BOOLEAN DEFAULT false
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    slug TEXT,
    tier TEXT,
    is_individual BOOLEAN,
    keys_used BIGINT,
    keys_limit INTEGER,
    total_requests BIGINT,
    unique_users BIGINT,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id,
        o.name,
        o.slug,
        o.tier,
        o.is_individual,
        COUNT(k.id) as keys_used,
        t.max_keys_per_email as keys_limit,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
        COUNT(DISTINCT k.email) as unique_users,
        o.is_active
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
    LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
    WHERE (include_individuals OR o.is_individual = false)
    AND o.is_active = true
    GROUP BY o.id, o.name, o.slug, o.tier, o.is_individual, t.max_keys_per_email, o.is_active
    ORDER BY keys_used DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION list_organizations_with_usage IS 'List organizations (excludes individuals unless include_individuals=true)';

-- New function: Get or create individual organization
CREATE OR REPLACE FUNCTION get_or_create_individual_org(
    user_email TEXT,
    user_tier TEXT DEFAULT 'free'
)
RETURNS UUID AS $$
DECLARE
    org_id UUID;
    user_slug TEXT;
BEGIN
    -- Generate slug from email
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

COMMENT ON FUNCTION get_or_create_individual_org IS 'Get or create a personal organization for an individual user';

-- New function: Get user's organization (for frontend routing)
CREATE OR REPLACE FUNCTION get_user_organization(user_email TEXT)
RETURNS TABLE (
    id UUID,
    name TEXT,
    slug TEXT,
    tier TEXT,
    is_individual BOOLEAN,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id,
        o.name,
        o.slug,
        o.tier,
        o.is_individual,
        o.is_active
    FROM organizations o
    JOIN api_keys k ON k.organization_id = o.id
    WHERE k.email = user_email
    AND k.is_active = true
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_organization IS 'Get organization for a user (for UI routing logic)';

-- ============================================
-- PHASE 5: VERIFICATION
-- ============================================

-- Show migration results
DO $$
DECLARE
    real_org_count INTEGER;
    individual_count INTEGER;
    orphaned_keys INTEGER;
BEGIN
    -- Count real organizations
    SELECT COUNT(*) INTO real_org_count
    FROM organizations
    WHERE is_individual = false AND is_active = true;

    -- Count individual orgs
    SELECT COUNT(*) INTO individual_count
    FROM organizations
    WHERE is_individual = true AND is_active = true;

    -- Count keys without valid org
    SELECT COUNT(*) INTO orphaned_keys
    FROM api_keys k
    WHERE NOT EXISTS (
        SELECT 1 FROM organizations o
        WHERE o.id = k.organization_id
        AND o.is_active = true
    );

    RAISE NOTICE '================================';
    RAISE NOTICE 'Migration Summary:';
    RAISE NOTICE '  Real Organizations: %', real_org_count;
    RAISE NOTICE '  Individual Users: %', individual_count;
    RAISE NOTICE '  Orphaned Keys: %', orphaned_keys;
    RAISE NOTICE '================================';

    IF orphaned_keys > 0 THEN
        RAISE WARNING 'Found % orphaned keys! Review manually.', orphaned_keys;
    END IF;
END $$;

-- ============================================
-- VERIFICATION QUERIES (for manual testing)
-- ============================================

-- List all real organizations:
-- SELECT * FROM list_organizations_with_usage(false);

-- List all individual users:
-- SELECT * FROM list_organizations_with_usage(true) WHERE is_individual = true;

-- Check a specific user's org:
-- SELECT * FROM get_user_organization('user@example.com');

-- View individual users analytics:
-- SELECT * FROM individual_users_summary;

-- View real organizations analytics:
-- SELECT * FROM organization_summary;
