-- Phase 2: Test digest() Function Directly
-- Run these tests in Supabase SQL Editor to verify digest() works with type casts
-- Date: 2025-12-10

-- Verify pgcrypto extension is enabled
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

-- Test 1: Both parameters explicitly cast (RECOMMENDED)
SELECT 'Test 1: Both params cast' as test_name,
       encode(digest('test@example.com'::bytea, 'sha256'::text), 'hex') as result;

-- Test 2: Only first parameter cast
SELECT 'Test 2: First param only' as test_name,
       encode(digest('test@example.com'::bytea, 'sha256'), 'hex') as result;

-- Test 3: No casts (expected to fail)
SELECT 'Test 3: No casts (should fail)' as test_name,
       encode(digest('test@example.com', 'sha256'), 'hex') as result;

-- Generate expected hash for 'user@example.com'
SELECT 'user-' || substring(
    encode(digest('user@example.com'::bytea, 'sha256'::text), 'hex'),
    1, 16
) as expected_slug;

-- Expected result: user-b4c9a289323b21a0 (or similar)
