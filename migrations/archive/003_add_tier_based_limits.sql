-- Migration: Add Tier-Based API Key Limits (Phase 3B)
-- Description: Different API key limits per company tier/plan
-- Date: 2025-12-10
-- Requires: 002_add_email_to_api_keys.sql

-- ============================================
-- TIER-BASED LIMITS
-- ============================================

-- Add tier column to track subscription level
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';

-- Create index for tier queries
CREATE INDEX IF NOT EXISTS idx_api_keys_tier 
    ON api_keys(tier);

-- Add check constraint for valid tiers
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'valid_tier_check'
        AND conrelid = 'api_keys'::regclass
    ) THEN
        ALTER TABLE api_keys
        ADD CONSTRAINT valid_tier_check
            CHECK (tier IN ('free', 'basic', 'professional', 'enterprise', 'custom'));
    END IF;
END $$;

COMMENT ON COLUMN api_keys.tier IS 'Subscription tier: free, basic, professional, enterprise, custom';

-- ============================================
-- TIER CONFIGURATION TABLE
-- ============================================

-- Table to store tier limits and features
CREATE TABLE IF NOT EXISTS api_key_tiers (
    tier_name TEXT PRIMARY KEY,
    max_keys_per_email INTEGER NOT NULL,
    rate_limit_per_minute INTEGER NOT NULL,
    rate_limit_per_hour INTEGER NOT NULL,
    rate_limit_per_day INTEGER NOT NULL,
    features JSONB DEFAULT '{}'::jsonb,
    price_monthly DECIMAL(10,2),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default tier configurations
INSERT INTO api_key_tiers (tier_name, max_keys_per_email, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day, price_monthly, description) VALUES
    ('free', 2, 10, 100, 1000, 0.00, 'Free tier - 2 keys, basic limits'),
    ('basic', 5, 30, 500, 5000, 29.00, 'Basic tier - 5 keys, standard limits'),
    ('professional', 10, 60, 1000, 10000, 99.00, 'Professional tier - 10 keys, high limits'),
    ('enterprise', 50, 120, 5000, 50000, 499.00, 'Enterprise tier - 50 keys, very high limits'),
    ('custom', 999, 999, 99999, 999999, NULL, 'Custom tier - negotiated limits')
ON CONFLICT (tier_name) DO NOTHING;

COMMENT ON TABLE api_key_tiers IS 'Configuration for different subscription tiers';

-- ============================================
-- UPDATED TRIGGER: Tier-Based Key Limit
-- ============================================

-- Drop old trigger and function
DROP TRIGGER IF EXISTS trigger_check_api_key_limit ON api_keys;
DROP FUNCTION IF EXISTS check_api_key_limit();

-- New function with tier-based limits
CREATE OR REPLACE FUNCTION check_api_key_limit_by_tier()
RETURNS TRIGGER AS $$
DECLARE
    current_key_count INTEGER;
    max_allowed INTEGER;
BEGIN
    -- Only check if email is provided
    IF NEW.email IS NOT NULL THEN
        -- Get current count of active keys for this email
        SELECT COUNT(*) INTO current_key_count
        FROM api_keys
        WHERE email = NEW.email AND is_active = true;
        
        -- Get max allowed for this tier
        SELECT max_keys_per_email INTO max_allowed
        FROM api_key_tiers
        WHERE tier_name = COALESCE(NEW.tier, 'free');
        
        -- If tier not found, default to free tier
        IF max_allowed IS NULL THEN
            max_allowed := 2;
        END IF;
        
        -- Check if limit exceeded
        IF current_key_count >= max_allowed THEN
            RAISE EXCEPTION 'Maximum % API keys allowed for % tier', max_allowed, COALESCE(NEW.tier, 'free');
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create new trigger
CREATE TRIGGER trigger_check_api_key_limit_by_tier
    BEFORE INSERT ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION check_api_key_limit_by_tier();

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get tier limits
CREATE OR REPLACE FUNCTION get_tier_info(tier_name TEXT)
RETURNS TABLE (
    tier TEXT,
    max_keys INTEGER,
    rate_minute INTEGER,
    rate_hour INTEGER,
    rate_day INTEGER,
    price DECIMAL,
    description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.tier_name,
        t.max_keys_per_email,
        t.rate_limit_per_minute,
        t.rate_limit_per_hour,
        t.rate_limit_per_day,
        t.price_monthly,
        t.description
    FROM api_key_tiers t
    WHERE t.tier_name = get_tier_info.tier_name;
END;
$$ LANGUAGE plpgsql;

-- Function to get key usage by tier
CREATE OR REPLACE FUNCTION get_keys_by_tier_and_email(user_email TEXT, user_tier TEXT)
RETURNS TABLE (
    id UUID,
    client_name TEXT,
    key_prefix TEXT,
    is_active BOOLEAN,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    total_requests BIGINT,
    keys_used INTEGER,
    keys_available INTEGER
) AS $$
DECLARE
    max_keys INTEGER;
    used_keys INTEGER;
BEGIN
    -- Get max keys for tier
    SELECT max_keys_per_email INTO max_keys
    FROM api_key_tiers
    WHERE tier_name = user_tier;
    
    -- Get current usage
    SELECT COUNT(*) INTO used_keys
    FROM api_keys
    WHERE email = user_email AND is_active = true;
    
    RETURN QUERY
    SELECT 
        k.id,
        k.client_name,
        k.key_prefix,
        k.is_active,
        k.created_at,
        k.expires_at,
        k.total_requests,
        used_keys,
        (max_keys - used_keys) as available
    FROM api_keys k
    WHERE k.email = user_email
    ORDER BY k.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to upgrade/downgrade tier
CREATE OR REPLACE FUNCTION change_user_tier(
    user_email TEXT,
    new_tier TEXT
) RETURNS TEXT AS $$
DECLARE
    current_count INTEGER;
    new_max INTEGER;
BEGIN
    -- Get current active key count
    SELECT COUNT(*) INTO current_count
    FROM api_keys
    WHERE email = user_email AND is_active = true;
    
    -- Get new tier limit
    SELECT max_keys_per_email INTO new_max
    FROM api_key_tiers
    WHERE tier_name = new_tier;
    
    -- Check if user has more keys than new tier allows
    IF current_count > new_max THEN
        RETURN FORMAT('Cannot downgrade: User has %s active keys but %s tier only allows %s', 
                      current_count, new_tier, new_max);
    END IF;
    
    -- Update all user's keys to new tier
    UPDATE api_keys
    SET tier = new_tier
    WHERE email = user_email;
    
    RETURN FORMAT('Successfully changed %s to %s tier', user_email, new_tier);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VIEWS FOR REPORTING
-- ============================================

-- View: Key usage by tier
CREATE OR REPLACE VIEW tier_usage_summary AS
SELECT 
    t.tier_name,
    t.max_keys_per_email,
    COUNT(DISTINCT k.email) as total_users,
    COUNT(k.id) as total_keys,
    COUNT(k.id) FILTER (WHERE k.is_active = true) as active_keys,
    COALESCE(SUM(k.total_requests), 0) as total_requests,
    ROUND(AVG(CASE WHEN k.is_active THEN 1 ELSE 0 END) * 100, 2) as active_percentage
FROM api_key_tiers t
LEFT JOIN api_keys k ON k.tier = t.tier_name
GROUP BY t.tier_name, t.max_keys_per_email
ORDER BY t.max_keys_per_email DESC;

COMMENT ON VIEW tier_usage_summary IS 'Summary statistics of API key usage by tier';

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- View tier configurations:
-- SELECT * FROM api_key_tiers ORDER BY max_keys_per_email;

-- View tier usage summary:
-- SELECT * FROM tier_usage_summary;

-- Get tier info:
-- SELECT * FROM get_tier_info('professional');

-- Check user's keys and limits:
-- SELECT * FROM get_keys_by_tier_and_email('user@example.com', 'professional');

-- ============================================
-- MIGRATION HELPER: Update Existing Keys
-- ============================================

-- Update existing keys to appropriate tier
-- Option 1: Set all to free tier
-- UPDATE api_keys SET tier = 'free' WHERE tier IS NULL;

-- Option 2: Set based on organization
-- UPDATE api_keys SET tier = 'professional' WHERE organization = 'The Jo Law Firm';
-- UPDATE api_keys SET tier = 'basic' WHERE organization = 'Moohan, Inc.';

-- ============================================
-- ROLLBACK (if needed)
-- ============================================

-- To rollback this migration:
-- DROP VIEW IF EXISTS tier_usage_summary;
-- DROP FUNCTION IF EXISTS change_user_tier(TEXT, TEXT);
-- DROP FUNCTION IF EXISTS get_keys_by_tier_and_email(TEXT, TEXT);
-- DROP FUNCTION IF EXISTS get_tier_info(TEXT);
-- DROP TRIGGER IF EXISTS trigger_check_api_key_limit_by_tier ON api_keys;
-- DROP FUNCTION IF EXISTS check_api_key_limit_by_tier();
-- DROP TABLE IF EXISTS api_key_tiers;
-- ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS valid_tier_check;
-- DROP INDEX IF EXISTS idx_api_keys_tier;
-- ALTER TABLE api_keys DROP COLUMN IF EXISTS tier;

COMMENT ON TABLE api_keys IS 'Phase 3B: Now supports tier-based key limits and rate limiting';

