-- ============================================
-- COMPLETE DATABASE STRUCTURE
-- ============================================
-- Description: Comprehensive database setup for API key authentication
-- Date: 2025-12-10
-- Purpose: Clean structure with organizations, tiers, and API keys
--
-- This migration can be run on a fresh database OR to reset existing structure
-- ============================================

-- ============================================
-- PHASE 0: ENABLE REQUIRED EXTENSIONS
-- ============================================

-- Enable pgcrypto for digest() and gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable other useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PHASE 1: DROP EXISTING STRUCTURES (Clean Slate)
-- ============================================

-- Drop in reverse dependency order
DROP VIEW IF EXISTS individual_users_summary CASCADE;
DROP VIEW IF EXISTS organization_summary CASCADE;
DROP VIEW IF EXISTS tier_usage_summary CASCADE;

DROP FUNCTION IF EXISTS get_or_create_individual_org(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_user_organization(TEXT) CASCADE;
DROP FUNCTION IF EXISTS list_organizations_with_usage(BOOLEAN) CASCADE;
DROP FUNCTION IF EXISTS get_organization_usage(UUID) CASCADE;
DROP FUNCTION IF EXISTS get_keys_by_organization(UUID) CASCADE;
DROP FUNCTION IF EXISTS change_organization_tier(UUID, TEXT) CASCADE;
DROP FUNCTION IF EXISTS change_user_tier(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_keys_by_tier_and_email(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_keys_by_email(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_tier_info(TEXT) CASCADE;
DROP FUNCTION IF EXISTS check_api_key_limit_by_organization() CASCADE;
DROP FUNCTION IF EXISTS check_api_key_limit_by_tier() CASCADE;
DROP FUNCTION IF EXISTS check_api_key_limit() CASCADE;
DROP FUNCTION IF EXISTS check_rate_limit(UUID, VARCHAR, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS get_api_key_usage_stats(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS deactivate_expired_api_keys() CASCADE;

DROP TRIGGER IF EXISTS trigger_check_api_key_limit_by_organization ON api_keys;
DROP TRIGGER IF EXISTS trigger_check_api_key_limit_by_tier ON api_keys;
DROP TRIGGER IF EXISTS trigger_check_api_key_limit ON api_keys;

DROP TABLE IF EXISTS api_key_usage CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS api_key_tiers CASCADE;

-- ============================================
-- PHASE 2: CREATE TIER CONFIGURATION TABLE
-- ============================================

CREATE TABLE api_key_tiers (
    tier_name TEXT PRIMARY KEY,
    max_keys_per_organization INTEGER NOT NULL,
    rate_limit_per_minute INTEGER NOT NULL,
    rate_limit_per_hour INTEGER NOT NULL,
    rate_limit_per_day INTEGER NOT NULL,
    features JSONB DEFAULT '{}'::jsonb,
    price_monthly DECIMAL(10,2),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert tier configurations
INSERT INTO api_key_tiers (tier_name, max_keys_per_organization, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day, price_monthly, description) VALUES
    ('free', 2, 10, 100, 1000, 0.00, 'Free tier - 2 keys, basic limits'),
    ('basic', 5, 30, 500, 5000, 29.00, 'Basic tier - 5 keys, standard limits'),
    ('professional', 10, 60, 1000, 10000, 99.00, 'Professional tier - 10 keys, high limits'),
    ('enterprise', 50, 120, 5000, 50000, 499.00, 'Enterprise tier - 50 keys, very high limits'),
    ('custom', 999, 999, 99999, 999999, NULL, 'Custom tier - negotiated limits');

COMMENT ON TABLE api_key_tiers IS 'Subscription tiers with rate limits and key allowances';
COMMENT ON COLUMN api_key_tiers.max_keys_per_organization IS 'Maximum API keys per organization';

-- ============================================
-- PHASE 3: CREATE ORGANIZATIONS TABLE
-- ============================================

CREATE TABLE organizations (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Organization details
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,

    -- Type flag
    is_individual BOOLEAN DEFAULT false,

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
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_tier ON organizations(tier);
CREATE INDEX idx_organizations_is_active ON organizations(is_active);
CREATE INDEX idx_organizations_is_individual ON organizations(is_individual);
CREATE INDEX idx_organizations_primary_contact_email ON organizations(primary_contact_email);

COMMENT ON TABLE organizations IS 'Organizations (both companies and individual users)';
COMMENT ON COLUMN organizations.slug IS 'Unique URL-safe identifier';
COMMENT ON COLUMN organizations.is_individual IS 'True for personal orgs, false for companies';
COMMENT ON COLUMN organizations.tier IS 'Subscription tier for the organization';

-- ============================================
-- PHASE 4: CREATE API_KEYS TABLE
-- ============================================

CREATE TABLE api_keys (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Key storage (NEVER store plaintext!)
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,

    -- Client information
    client_name TEXT NOT NULL,
    description TEXT,
    email TEXT,

    -- Organization relationship
    organization_id UUID REFERENCES organizations(id),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Legacy fields (kept for backwards compatibility)
    tier TEXT DEFAULT 'free',
    organization TEXT,

    -- Status & lifecycle
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- Rate limiting (per-key overrides)
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,

    -- Tracking
    total_requests BIGINT DEFAULT 0,
    created_by TEXT
);

-- Indexes
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash) WHERE is_active = true;
CREATE INDEX idx_api_keys_client_name ON api_keys(client_name);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_api_keys_organization_id ON api_keys(organization_id);
CREATE INDEX idx_api_keys_email ON api_keys(email);
CREATE INDEX idx_api_keys_tier ON api_keys(tier);

COMMENT ON TABLE api_keys IS 'API keys with organization-based limits';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the actual API key (never store plaintext)';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 characters of key for display';
COMMENT ON COLUMN api_keys.organization_id IS 'Foreign key to organizations table';
COMMENT ON COLUMN api_keys.tier IS 'DEPRECATED: Use organizations.tier instead (kept for compatibility)';
COMMENT ON COLUMN api_keys.organization IS 'DEPRECATED: Use organization_id instead (kept for display)';

-- ============================================
-- PHASE 5: CREATE API_KEY_USAGE TABLE
-- ============================================

CREATE TABLE api_key_usage (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,

    -- Request details
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,

    -- Client info
    ip_address INET,
    user_agent TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX idx_api_key_usage_key_id_timestamp ON api_key_usage(api_key_id, timestamp DESC);
CREATE INDEX idx_api_key_usage_recent ON api_key_usage(api_key_id, timestamp);

COMMENT ON TABLE api_key_usage IS 'Tracks every API request for analytics and rate limiting';

-- ============================================
-- PHASE 6: ROW LEVEL SECURITY
-- ============================================

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_tiers ENABLE ROW LEVEL SECURITY;

-- Service role policies
CREATE POLICY "Service role full access api_keys"
    ON api_keys FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access api_key_usage"
    ON api_key_usage FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access organizations"
    ON organizations FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access api_key_tiers"
    ON api_key_tiers FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================
-- PHASE 7: CORE FUNCTIONS
-- ============================================

-- Function: Get or create individual organization
CREATE OR REPLACE FUNCTION get_or_create_individual_org(
    user_email TEXT,
    user_tier TEXT DEFAULT 'free'
)
RETURNS UUID AS $$
DECLARE
    org_id UUID;
    user_slug TEXT;
BEGIN
    -- Generate slug from email hash
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_or_create_individual_org IS 'Get or create personal organization for individual user';

-- Function: Check organization key limit (trigger function)
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
    SELECT max_keys_per_organization INTO max_allowed
    FROM api_key_tiers
    WHERE tier_name = org_tier;

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

-- Create trigger
CREATE TRIGGER trigger_check_api_key_limit_by_organization
    BEFORE INSERT ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION check_api_key_limit_by_organization();

COMMENT ON FUNCTION check_api_key_limit_by_organization IS 'Enforces API key limits at organization level';

-- Function: Deactivate expired keys
CREATE OR REPLACE FUNCTION deactivate_expired_api_keys()
RETURNS INTEGER AS $$
DECLARE
    affected_count INTEGER;
BEGIN
    UPDATE api_keys
    SET is_active = false
    WHERE is_active = true
      AND expires_at IS NOT NULL
      AND expires_at < NOW();

    GET DIAGNOSTICS affected_count = ROW_COUNT;
    RETURN affected_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION deactivate_expired_api_keys IS 'Deactivates expired API keys';

-- Function: Check rate limit
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_api_key_id UUID,
    p_period VARCHAR(10),
    p_limit INTEGER
)
RETURNS TABLE(
    is_within_limit BOOLEAN,
    current_count BIGINT,
    limit_value INTEGER
) AS $$
DECLARE
    v_interval INTERVAL;
    v_count BIGINT;
BEGIN
    CASE p_period
        WHEN 'minute' THEN v_interval := '1 minute'::INTERVAL;
        WHEN 'hour' THEN v_interval := '1 hour'::INTERVAL;
        WHEN 'day' THEN v_interval := '1 day'::INTERVAL;
        ELSE RAISE EXCEPTION 'Invalid period: %. Must be minute, hour, or day', p_period;
    END CASE;

    SELECT COUNT(*) INTO v_count
    FROM api_key_usage
    WHERE api_key_id = p_api_key_id
      AND timestamp >= NOW() - v_interval;

    RETURN QUERY
    SELECT
        (v_count < p_limit) AS is_within_limit,
        v_count AS current_count,
        p_limit AS limit_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_rate_limit IS 'Check if API key has exceeded rate limit';

-- Function: Get API key usage stats
CREATE OR REPLACE FUNCTION get_api_key_usage_stats(
    p_api_key_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE(
    date DATE,
    total_requests BIGINT,
    successful_requests BIGINT,
    failed_requests BIGINT,
    avg_response_time_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(timestamp) AS date,
        COUNT(*)::BIGINT AS total_requests,
        COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 400)::BIGINT AS successful_requests,
        COUNT(*) FILTER (WHERE status_code >= 400)::BIGINT AS failed_requests,
        ROUND(AVG((metadata->>'response_time_ms')::NUMERIC), 2) AS avg_response_time_ms
    FROM api_key_usage
    WHERE api_key_id = p_api_key_id
      AND timestamp >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY DATE(timestamp)
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_api_key_usage_stats IS 'Get daily usage statistics for an API key';

-- ============================================
-- PHASE 8: ORGANIZATION MANAGEMENT FUNCTIONS
-- ============================================

-- Function: Get user's organization
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
    WHERE o.primary_contact_email = user_email
    AND o.is_active = true
    ORDER BY o.is_individual DESC  -- Prioritize real orgs over personal
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_organization IS 'Get organization for a user';

-- Function: Get keys by organization
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

-- Function: Get organization usage
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
    SELECT o.tier INTO org_tier
    FROM organizations o
    WHERE o.id = org_id;

    SELECT max_keys_per_organization INTO tier_limit
    FROM api_key_tiers
    WHERE tier_name = org_tier;

    RETURN QUERY
    SELECT
        o.name,
        o.tier,
        COUNT(k.id)::INTEGER as keys_used,
        tier_limit as keys_limit,
        (tier_limit - COUNT(k.id))::INTEGER as keys_available,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
        COUNT(k.id) FILTER (WHERE k.is_active = true)::INTEGER as active_keys,
        COUNT(DISTINCT k.email)::INTEGER as unique_users
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id
    WHERE o.id = org_id
    GROUP BY o.name, o.tier;
END;
$$ LANGUAGE plpgsql;

-- Function: List organizations with usage
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
        t.max_keys_per_organization as keys_limit,
        COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
        COUNT(DISTINCT k.email) as unique_users,
        o.is_active
    FROM organizations o
    LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
    LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
    WHERE (include_individuals OR o.is_individual = false)
    AND o.is_active = true
    GROUP BY o.id, o.name, o.slug, o.tier, o.is_individual, t.max_keys_per_organization, o.is_active
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
    SELECT name INTO org_name FROM organizations WHERE id = org_id;

    IF org_name IS NULL THEN
        RETURN 'Organization not found';
    END IF;

    SELECT COUNT(*) INTO current_count
    FROM api_keys
    WHERE organization_id = org_id AND is_active = true;

    SELECT max_keys_per_organization INTO new_max
    FROM api_key_tiers
    WHERE tier_name = new_tier;

    IF current_count > new_max THEN
        RETURN FORMAT('Cannot downgrade "%s": Has %s active keys but %s tier only allows %s',
                      org_name, current_count, new_tier, new_max);
    END IF;

    UPDATE organizations
    SET tier = new_tier, updated_at = NOW()
    WHERE id = org_id;

    UPDATE api_keys
    SET tier = new_tier
    WHERE organization_id = org_id;

    RETURN FORMAT('Successfully changed "%s" to %s tier', org_name, new_tier);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- PHASE 9: REPORTING VIEWS
-- ============================================

-- View: Organization summary (real companies only)
CREATE VIEW organization_summary AS
SELECT
    o.id,
    o.name,
    o.slug,
    o.tier,
    o.primary_contact_email,
    t.max_keys_per_organization as keys_limit,
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
WHERE o.is_individual = false
AND o.is_active = true
GROUP BY o.id, o.name, o.slug, o.tier, o.primary_contact_email, t.max_keys_per_organization, t.price_monthly, o.created_at, o.is_active
ORDER BY total_requests DESC;

COMMENT ON VIEW organization_summary IS 'Real organizations only (excludes personal orgs)';

-- View: Individual users summary
CREATE VIEW individual_users_summary AS
SELECT
    o.id,
    o.primary_contact_email as email,
    o.tier,
    t.max_keys_per_organization as keys_limit,
    COUNT(k.id) as keys_used,
    COUNT(k.id) FILTER (WHERE k.is_active = true) as active_keys,
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests,
    o.created_at,
    o.is_active
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.is_individual = true
AND o.is_active = true
GROUP BY o.id, o.primary_contact_email, o.tier, t.max_keys_per_organization, o.created_at, o.is_active
ORDER BY total_requests DESC;

COMMENT ON VIEW individual_users_summary IS 'Individual users only (personal orgs)';

-- View: Tier usage summary
CREATE VIEW tier_usage_summary AS
SELECT
    t.tier_name,
    t.max_keys_per_organization,
    COUNT(DISTINCT o.id) FILTER (WHERE o.is_individual = false) as organizations,
    COUNT(DISTINCT o.id) FILTER (WHERE o.is_individual = true) as individuals,
    COUNT(k.id) as total_keys,
    COUNT(k.id) FILTER (WHERE k.is_active = true) as active_keys,
    COALESCE(SUM(k.total_requests), 0)::BIGINT as total_requests
FROM api_key_tiers t
LEFT JOIN organizations o ON o.tier = t.tier_name AND o.is_active = true
LEFT JOIN api_keys k ON k.organization_id = o.id
GROUP BY t.tier_name, t.max_keys_per_organization
ORDER BY t.max_keys_per_organization DESC;

COMMENT ON VIEW tier_usage_summary IS 'Usage statistics by tier';

-- ============================================
-- PHASE 10: VERIFICATION
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '================================';
    RAISE NOTICE 'Database structure created successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - api_key_tiers (5 tiers)';
    RAISE NOTICE '  - organizations';
    RAISE NOTICE '  - api_keys';
    RAISE NOTICE '  - api_key_usage';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - get_or_create_individual_org()';
    RAISE NOTICE '  - check_api_key_limit_by_organization()';
    RAISE NOTICE '  - get_user_organization()';
    RAISE NOTICE '  - get_keys_by_organization()';
    RAISE NOTICE '  - get_organization_usage()';
    RAISE NOTICE '  - list_organizations_with_usage()';
    RAISE NOTICE '  - change_organization_tier()';
    RAISE NOTICE '  - check_rate_limit()';
    RAISE NOTICE '  - get_api_key_usage_stats()';
    RAISE NOTICE '  - deactivate_expired_api_keys()';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - organization_summary';
    RAISE NOTICE '  - individual_users_summary';
    RAISE NOTICE '  - tier_usage_summary';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready to create API keys!';
    RAISE NOTICE '================================';
END $$;
