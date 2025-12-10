-- Migration: Create API Keys Tables
-- Description: Database-backed API key authentication with usage tracking
-- Date: 2025-12-10

-- ============================================
-- TABLE 1: api_keys
-- ============================================
-- Purpose: Store API keys with metadata, expiration, and rate limits
-- Security: Stores SHA-256 hashes only (NEVER plaintext keys)

CREATE TABLE IF NOT EXISTS api_keys (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Key storage (NEVER store plaintext!)
    key_hash TEXT NOT NULL UNIQUE,          -- SHA-256 hash of actual key
    key_prefix TEXT NOT NULL,                -- First 8 chars for display (e.g., "api_abc1...")

    -- Client information
    client_name TEXT NOT NULL,               -- Human-readable name (e.g., "ProductionAPI")
    description TEXT,                        -- Optional notes

    -- Metadata (JSONB for flexibility)
    metadata JSONB DEFAULT '{}'::jsonb,      -- Custom fields: scopes, permissions, etc.

    -- Status & lifecycle
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,                  -- NULL = never expires

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,

    -- Tracking
    total_requests BIGINT DEFAULT 0,
    created_by TEXT                          -- Who created this key (email or name)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash
    ON api_keys(key_hash)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_api_keys_client_name
    ON api_keys(client_name);

CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at
    ON api_keys(expires_at)
    WHERE expires_at IS NOT NULL;

COMMENT ON TABLE api_keys IS 'Stores API keys with metadata, expiration, and rate limits';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the actual API key (never store plaintext)';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 characters of key for display purposes';
COMMENT ON COLUMN api_keys.metadata IS 'Flexible JSONB field for scopes, permissions, etc.';

-- ============================================
-- TABLE 2: api_key_usage
-- ============================================
-- Purpose: Track every API request for analytics and rate limiting

CREATE TABLE IF NOT EXISTS api_key_usage (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to api_keys
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,

    -- Request details
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    endpoint TEXT NOT NULL,                  -- e.g., "/mcp/v1/tools/call"
    method TEXT NOT NULL,                    -- GET, POST, etc.
    status_code INTEGER,                     -- 200, 401, 500, etc.

    -- Client info
    ip_address INET,
    user_agent TEXT,

    -- Optional: Request metadata
    metadata JSONB DEFAULT '{}'::jsonb       -- tool_name, query, response_time, etc.
);

-- Indexes for analytics and rate limiting
CREATE INDEX IF NOT EXISTS idx_api_key_usage_key_id_timestamp
    ON api_key_usage(api_key_id, timestamp DESC);

-- Partial index for recent data (optimize rate limiting queries)
CREATE INDEX IF NOT EXISTS idx_api_key_usage_recent
    ON api_key_usage(api_key_id, timestamp)
    WHERE timestamp > NOW() - INTERVAL '7 days';

COMMENT ON TABLE api_key_usage IS 'Tracks every API request for analytics and rate limiting';
COMMENT ON COLUMN api_key_usage.metadata IS 'Optional JSONB field for tool_name, query params, response time, etc.';

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
-- Purpose: Ensure security even if service key is compromised

-- Enable RLS on both tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_usage ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can read/write all rows
CREATE POLICY "Service role has full access to api_keys"
    ON api_keys
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to api_key_usage"
    ON api_key_usage
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Note: No public access - only service role can access these tables

-- ============================================
-- HELPER FUNCTION: Clean up expired keys
-- ============================================
-- Purpose: Periodically deactivate expired keys (can be called manually or via cron)

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

COMMENT ON FUNCTION deactivate_expired_api_keys IS 'Deactivates API keys that have passed their expiration date';

-- ============================================
-- HELPER FUNCTION: Get API key usage statistics
-- ============================================
-- Purpose: Retrieve usage statistics for an API key over a specified time period

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

COMMENT ON FUNCTION get_api_key_usage_stats IS 'Returns daily usage statistics for an API key over the specified number of days';

-- ============================================
-- HELPER FUNCTION: Check rate limit
-- ============================================
-- Purpose: Check if an API key has exceeded its rate limit for a given period

CREATE OR REPLACE FUNCTION check_rate_limit(
    p_api_key_id UUID,
    p_period VARCHAR(10),  -- 'minute', 'hour', or 'day'
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
    -- Determine time interval
    CASE p_period
        WHEN 'minute' THEN v_interval := '1 minute'::INTERVAL;
        WHEN 'hour' THEN v_interval := '1 hour'::INTERVAL;
        WHEN 'day' THEN v_interval := '1 day'::INTERVAL;
        ELSE RAISE EXCEPTION 'Invalid period: %. Must be minute, hour, or day', p_period;
    END CASE;

    -- Count requests in the period
    SELECT COUNT(*) INTO v_count
    FROM api_key_usage
    WHERE api_key_id = p_api_key_id
      AND timestamp >= NOW() - v_interval;

    -- Return result
    RETURN QUERY
    SELECT
        (v_count < p_limit) AS is_within_limit,
        v_count AS current_count,
        p_limit AS limit_value;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_rate_limit IS 'Checks if an API key has exceeded its rate limit for a specified time period';

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these to verify the migration succeeded:

-- Check tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('api_keys', 'api_key_usage');

-- Check indexes exist
-- SELECT indexname FROM pg_indexes WHERE tablename IN ('api_keys', 'api_key_usage');

-- Check RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename IN ('api_keys', 'api_key_usage');

-- Test insert (should fail if RLS is working correctly without service role)
-- INSERT INTO api_keys (client_name, key_hash, key_prefix) VALUES ('Test', 'hash123', 'api_test');

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
