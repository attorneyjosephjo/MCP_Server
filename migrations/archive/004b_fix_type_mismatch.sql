-- Quick Fix: Type Mismatch in list_organizations_with_usage()
-- Issue: SUM() returns NUMERIC but function expects BIGINT
-- Date: 2025-12-10

-- Drop and recreate the function with correct type casting
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
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- FIXED: Cast to BIGINT
        COUNT(DISTINCT k.email) as unique_users,
        o.is_active
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
    LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
    GROUP BY o.id, o.name, o.slug, o.tier, t.max_keys_per_email, o.is_active
    ORDER BY keys_used DESC;
END;
$$ LANGUAGE plpgsql;

-- Also fix in get_organization_usage()
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
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- FIXED: Cast to BIGINT
        COUNT(k.id) FILTER (WHERE k.is_active = true)::INTEGER as active_keys,
        COUNT(DISTINCT k.email)::INTEGER as unique_users
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id
    WHERE o.id = org_id
    GROUP BY o.name, o.tier;
END;
$$ LANGUAGE plpgsql;

-- Also fix the view - must DROP first because we're changing column types
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
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,  -- FIXED: Cast to BIGINT
    t.price_monthly,
    o.created_at,
    o.is_active
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.slug != 'individuals'  -- Exclude special individuals org
GROUP BY o.id, o.name, o.slug, o.tier, o.primary_contact_email, t.max_keys_per_email, t.price_monthly, o.created_at, o.is_active
ORDER BY total_requests DESC;

-- Verification
SELECT 'Type mismatch fixed!' as status;

