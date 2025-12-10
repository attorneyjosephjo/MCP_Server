-- Migration: Organizations Table and Organization-Based Limits (Phase 3C)
-- Description: Proper organization management with unique IDs and org-level limits
-- Date: 2025-12-10
-- Requires: 003_add_tier_based_limits.sql

-- ============================================
-- ORGANIZATIONS TABLE
-- ============================================

-- Table to store unique organizations
CREATE TABLE IF NOT EXISTS organizations (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Organization details
    name TEXT NOT NULL,                      -- Display name (can duplicate)
    slug TEXT UNIQUE NOT NULL,               -- Unique identifier (e.g., "smith-law-firm-ca")
    
    -- Subscription
    tier TEXT DEFAULT 'free' REFERENCES api_key_tiers(tier_name),
    
    -- Contact info
    primary_contact_email TEXT,
    billing_email TEXT,
    website TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_tier ON organizations(tier);
CREATE INDEX IF NOT EXISTS idx_organizations_is_active ON organizations(is_active);

COMMENT ON TABLE organizations IS 'Unique organizations with tier-based limits';
COMMENT ON COLUMN organizations.slug IS 'Unique URL-safe identifier (e.g., "acme-corp-ny")';
COMMENT ON COLUMN organizations.tier IS 'Subscription tier for the entire organization';

-- ============================================
-- SPECIAL ORGANIZATION: Individuals
-- ============================================

-- Create a special organization for individual users (no company)
INSERT INTO organizations (id, name, slug, tier, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Individual Users',
    'individuals',
    'free',
    true
) ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE organizations IS 'Organizations table - includes special "individuals" org for solo users';

-- ============================================
-- UPDATE API_KEYS TABLE
-- ============================================

-- Add organization_id column
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- Create index
CREATE INDEX IF NOT EXISTS idx_api_keys_organization_id ON api_keys(organization_id);

-- Backfill: Create organizations from existing organization names
DO $$
DECLARE
    org_record RECORD;
    new_org_id UUID;
BEGIN
    -- For each unique organization name in api_keys
    FOR org_record IN 
        SELECT DISTINCT organization 
        FROM api_keys 
        WHERE organization IS NOT NULL 
        AND organization_id IS NULL
    LOOP
        -- Create organization (generate slug from name)
        INSERT INTO organizations (name, slug, tier)
        VALUES (
            org_record.organization,
            lower(regexp_replace(org_record.organization, '[^a-zA-Z0-9]+', '-', 'g')),
            'free'  -- Default to free, admin can upgrade
        )
        ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
        RETURNING id INTO new_org_id;
        
        -- Update api_keys to reference this organization
        UPDATE api_keys 
        SET organization_id = new_org_id
        WHERE organization = org_record.organization 
        AND organization_id IS NULL;
    END LOOP;
    
    -- Handle keys without organization (assign to "individuals")
    UPDATE api_keys 
    SET organization_id = '00000000-0000-0000-0000-000000000000'
    WHERE organization IS NULL 
    AND organization_id IS NULL;
END $$;

COMMENT ON COLUMN api_keys.organization_id IS 'Foreign key to organizations table (replaces organization name)';

-- ============================================
-- UPDATED TRIGGER: Organization-Based Limits
-- ============================================

-- Drop old trigger and function
DROP TRIGGER IF EXISTS trigger_check_api_key_limit_by_tier ON api_keys;
DROP FUNCTION IF EXISTS check_api_key_limit_by_tier();

-- New function: Check limits at ORGANIZATION level
CREATE OR REPLACE FUNCTION check_api_key_limit_by_organization()
RETURNS TRIGGER AS $$
DECLARE
    org_key_count INTEGER;
    org_tier TEXT;
    max_allowed INTEGER;
    org_name TEXT;
BEGIN
    -- Get organization's tier
    SELECT o.tier, o.name INTO org_tier, org_name
    FROM organizations o
    WHERE o.id = NEW.organization_id;
    
    -- If organization not found, reject
    IF org_tier IS NULL THEN
        RAISE EXCEPTION 'Organization not found';
    END IF;
    
    -- Get current count of ACTIVE keys for this ORGANIZATION
    SELECT COUNT(*) INTO org_key_count
    FROM api_keys
    WHERE organization_id = NEW.organization_id 
    AND is_active = true;
    
    -- Get max allowed for this organization's tier
    SELECT max_keys_per_email INTO max_allowed
    FROM api_key_tiers
    WHERE tier_name = org_tier;
    
    -- Rename column for clarity (it's really max_keys_per_org now)
    IF max_allowed IS NULL THEN
        max_allowed := 2;  -- Default to free tier
    END IF;
    
    -- Check if limit exceeded
    IF org_key_count >= max_allowed THEN
        RAISE EXCEPTION 'Organization "%" has reached maximum of % API keys for % tier', 
                        org_name, max_allowed, org_tier;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create new trigger
CREATE TRIGGER trigger_check_api_key_limit_by_organization
    BEFORE INSERT ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION check_api_key_limit_by_organization();

COMMENT ON FUNCTION check_api_key_limit_by_organization IS 'Enforces API key limits at ORGANIZATION level (not per user)';

-- ============================================
-- UPDATED HELPER FUNCTIONS
-- ============================================

-- Function: Get all keys for an organization
CREATE OR REPLACE FUNCTION get_keys_by_organization(org_id UUID)
RETURNS TABLE (
    id UUID,
    client_name TEXT,
    email TEXT,
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
        k.email,
        k.key_prefix,
        k.is_active,
        k.created_at,
        k.expires_at,
        k.total_requests
    FROM api_keys k
    WHERE k.organization_id = org_id
    ORDER BY k.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Get organization usage summary
CREATE OR REPLACE FUNCTION get_organization_usage(org_id UUID)
RETURNS TABLE (
    organization_name TEXT,
    tier TEXT,
    keys_used INTEGER,
    keys_limit INTEGER,
    keys_available INTEGER,
    total_requests BIGINT,
    active_keys INTEGER,
    unique_users INTEGER
) AS $$
DECLARE
    org_tier TEXT;
    tier_limit INTEGER;
BEGIN
    -- Get organization details
    SELECT o.tier INTO org_tier
    FROM organizations o
    WHERE o.id = org_id;
    
    -- Get tier limit
    SELECT max_keys_per_email INTO tier_limit
    FROM api_key_tiers
    WHERE tier_name = org_tier;
    
    RETURN QUERY
    SELECT 
        o.name,
        o.tier,
        COUNT(k.id)::INTEGER as keys_used,
        tier_limit as keys_limit,
        (tier_limit - COUNT(k.id))::INTEGER as keys_available,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- Cast to BIGINT
        COUNT(k.id) FILTER (WHERE k.is_active = true)::INTEGER as active_keys,
        COUNT(DISTINCT k.email)::INTEGER as unique_users
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id
    WHERE o.id = org_id
    GROUP BY o.name, o.tier;
END;
$$ LANGUAGE plpgsql;

-- Function: List all organizations with usage
CREATE OR REPLACE FUNCTION list_organizations_with_usage()
RETURNS TABLE (
    id UUID,
    name TEXT,
    slug TEXT,
    tier TEXT,
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
        COUNT(k.id) as keys_used,
        t.max_keys_per_email as keys_limit,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- Cast to BIGINT
        COUNT(DISTINCT k.email) as unique_users,
        o.is_active
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
    LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
    GROUP BY o.id, o.name, o.slug, o.tier, t.max_keys_per_email, o.is_active
    ORDER BY keys_used DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Change organization tier
CREATE OR REPLACE FUNCTION change_organization_tier(
    org_id UUID,
    new_tier TEXT
) RETURNS TEXT AS $$
DECLARE
    current_count INTEGER;
    new_max INTEGER;
    org_name TEXT;
BEGIN
    -- Get organization name
    SELECT name INTO org_name FROM organizations WHERE id = org_id;
    
    IF org_name IS NULL THEN
        RETURN 'Organization not found';
    END IF;
    
    -- Get current active key count
    SELECT COUNT(*) INTO current_count
    FROM api_keys
    WHERE organization_id = org_id AND is_active = true;
    
    -- Get new tier limit
    SELECT max_keys_per_email INTO new_max
    FROM api_key_tiers
    WHERE tier_name = new_tier;
    
    -- Check if organization has more keys than new tier allows
    IF current_count > new_max THEN
        RETURN FORMAT('Cannot downgrade "%s": Has %s active keys but %s tier only allows %s', 
                      org_name, current_count, new_tier, new_max);
    END IF;
    
    -- Update organization tier
    UPDATE organizations
    SET tier = new_tier, updated_at = NOW()
    WHERE id = org_id;
    
    -- Also update tier on all keys (for reporting)
    UPDATE api_keys
    SET tier = new_tier
    WHERE organization_id = org_id;
    
    RETURN FORMAT('Successfully changed "%s" to %s tier', org_name, new_tier);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VIEWS FOR REPORTING
-- ============================================

-- View: Organization summary
CREATE OR REPLACE VIEW organization_summary AS
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
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- Cast to BIGINT
    t.price_monthly,
    o.created_at,
    o.is_active
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.slug != 'individuals'  -- Exclude special individuals org
GROUP BY o.id, o.name, o.slug, o.tier, o.primary_contact_email, t.max_keys_per_email, t.price_monthly, o.created_at, o.is_active
ORDER BY total_requests DESC;

COMMENT ON VIEW organization_summary IS 'Summary of all organizations with usage stats';

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- List all organizations:
-- SELECT * FROM list_organizations_with_usage();

-- Get specific organization usage:
-- SELECT * FROM get_organization_usage('org-uuid-here');

-- Check individual users:
-- SELECT * FROM get_keys_by_organization('00000000-0000-0000-0000-000000000000');

-- ============================================
-- CLEANUP: Remove old email-based functions
-- ============================================

DROP FUNCTION IF EXISTS get_keys_by_email(TEXT);
DROP FUNCTION IF EXISTS get_keys_by_tier_and_email(TEXT, TEXT);
DROP FUNCTION IF EXISTS change_user_tier(TEXT, TEXT);

-- Keep these but mark as deprecated:
COMMENT ON COLUMN api_keys.tier IS 'DEPRECATED: Use organizations.tier instead (kept for backward compatibility)';
COMMENT ON COLUMN api_keys.organization IS 'DEPRECATED: Use organization_id instead (kept for display only)';

-- ============================================
-- RENAME MISLEADING COLUMN IN TIERS TABLE
-- ============================================

-- The column is really "max keys per ORGANIZATION" not per email
-- But we can't easily rename without breaking things
-- So just update the comment
COMMENT ON COLUMN api_key_tiers.max_keys_per_email IS 'Maximum API keys per ORGANIZATION (naming is legacy, actually org-level limit)';

-- ============================================
-- ROLLBACK (if needed)
-- ============================================

-- To rollback this migration:
-- DROP VIEW IF EXISTS organization_summary;
-- DROP FUNCTION IF EXISTS change_organization_tier(UUID, TEXT);
-- DROP FUNCTION IF EXISTS list_organizations_with_usage();
-- DROP FUNCTION IF EXISTS get_organization_usage(UUID);
-- DROP FUNCTION IF EXISTS get_keys_by_organization(UUID);
-- DROP TRIGGER IF EXISTS trigger_check_api_key_limit_by_organization ON api_keys;
-- DROP FUNCTION IF EXISTS check_api_key_limit_by_organization();
-- DROP INDEX IF EXISTS idx_api_keys_organization_id;
-- ALTER TABLE api_keys DROP COLUMN IF EXISTS organization_id;
-- DROP TABLE IF EXISTS organizations CASCADE;

COMMENT ON TABLE api_keys IS 'Phase 3C: Limits enforced at ORGANIZATION level, not per user';
COMMENT ON TABLE organizations IS 'Phase 3C: Organizations with unique IDs and tier-based limits';

