-- Phase 6: Verify the Fix
-- Run these queries in Supabase SQL Editor after applying the fix
-- Date: 2025-12-10

-- Test 1: Test the function directly (should return a UUID)
SELECT 'Testing get_or_create_individual_org...' as test_step;
SELECT get_or_create_individual_org('test@example.com', 'free') as org_id;

-- Test 2: Verify organization was created correctly
SELECT 'Verifying organization structure...' as test_step;
SELECT
    o.id,
    o.slug,
    o.name,
    o.is_individual,
    o.primary_contact_email,
    o.tier,
    o.is_active
FROM organizations o
WHERE primary_contact_email = 'test@example.com';

-- Expected results:
-- - slug starts with 'user-'
-- - is_individual = true
-- - primary_contact_email = 'test@example.com'

-- Test 3: Check function exists with correct signature
SELECT 'Checking function exists...' as test_step;
SELECT
    routine_name,
    routine_type,
    data_type as return_type
FROM information_schema.routines
WHERE routine_name = 'get_or_create_individual_org'
AND routine_schema = 'public';

-- Test 4: Verify the function is idempotent (calling twice returns same org)
SELECT 'Testing idempotency...' as test_step;
WITH first_call AS (
    SELECT get_or_create_individual_org('idempotent-test@example.com', 'free') as org_id
),
second_call AS (
    SELECT get_or_create_individual_org('idempotent-test@example.com', 'free') as org_id
)
SELECT
    first_call.org_id = second_call.org_id as is_idempotent,
    first_call.org_id,
    second_call.org_id
FROM first_call, second_call;

-- Expected: is_idempotent = true (both calls return the same UUID)

-- Clean up test data (optional - comment out if you want to keep test orgs)
-- DELETE FROM organizations WHERE primary_contact_email IN ('test@example.com', 'idempotent-test@example.com');

-- Test 5: View all individual organizations
SELECT 'Listing all individual organizations...' as test_step;
SELECT
    id,
    name,
    slug,
    tier,
    primary_contact_email,
    created_at,
    is_active
FROM organizations
WHERE is_individual = true
ORDER BY created_at DESC;
