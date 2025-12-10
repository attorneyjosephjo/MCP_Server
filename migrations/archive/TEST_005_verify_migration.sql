-- Test Script for Phase 3C: Notion-Style Individual Organizations
-- Run this after executing 005_split_individuals_into_separate_orgs.sql
-- Date: 2025-12-10
-- Compatible with Supabase SQL Editor and psql

-- ============================================
-- TEST 1: Verify is_individual Column Exists
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 1: Checking is_individual column...';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'organizations'
AND column_name = 'is_individual';

-- Expected: One row with is_individual column, type boolean, nullable NO

-- ============================================
-- TEST 2: Count Organizations by Type
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 2: Counting organizations by type...';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    CASE WHEN is_individual THEN 'Individual Users' ELSE 'Real Organizations' END as type,
    COUNT(*) as total,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active,
    COUNT(CASE WHEN is_active = false THEN 1 END) as inactive
FROM organizations
GROUP BY is_individual
ORDER BY is_individual;

-- Expected: At least 2 rows (individuals and organizations)
-- Expected: Old shared "individuals" org should be in inactive count

-- ============================================
-- TEST 3: Verify Old Shared Org is Inactive
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 3: Checking old shared org status...';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    id,
    name,
    slug,
    is_individual,
    is_active,
    CASE
        WHEN id = '00000000-0000-0000-0000-000000000000' AND is_active = false
        THEN '✅ PASS - Old shared org is inactive'
        ELSE '❌ FAIL - Old shared org still active'
    END as test_result
FROM organizations
WHERE id = '00000000-0000-0000-0000-000000000000';

-- Expected: is_active = false, test_result = PASS

-- ============================================
-- TEST 4: Verify Each Email Has Own Organization
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 4: Checking email to org mapping...';
    RAISE NOTICE '==========================================';
END $$;

-- Show sample of individual orgs
SELECT
    o.slug,
    o.is_individual,
    o.primary_contact_email,
    o.tier,
    COUNT(k.id) as key_count
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
WHERE o.is_individual = true
AND o.is_active = true
GROUP BY o.id, o.slug, o.is_individual, o.primary_contact_email, o.tier
ORDER BY key_count DESC
LIMIT 10;

-- Expected: Each row has unique email, is_individual = true, slug like user-xxx

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Checking for emails with multiple organizations...';
END $$;

-- Check for emails with multiple organizations (should be 0)
SELECT
    k.email,
    COUNT(DISTINCT k.organization_id) as org_count,
    CASE
        WHEN COUNT(DISTINCT k.organization_id) = 1 THEN '✅ PASS'
        ELSE '❌ FAIL - Email has multiple orgs'
    END as test_result
FROM api_keys k
JOIN organizations o ON o.id = k.organization_id
WHERE k.email IS NOT NULL
AND o.is_active = true
GROUP BY k.email
HAVING COUNT(DISTINCT k.organization_id) > 1;

-- Expected: 0 rows (no email should have multiple orgs)

-- ============================================
-- TEST 5: Check for Orphaned Keys
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 5: Checking for orphaned keys...';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    COUNT(*) as orphaned_count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ PASS - No orphaned keys'
        ELSE '❌ FAIL - Found orphaned keys'
    END as test_result
FROM api_keys k
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o
    WHERE o.id = k.organization_id
    AND o.is_active = true
);

-- Expected: 0 orphaned keys

-- ============================================
-- TEST 6: Verify Individual Org Naming Pattern
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 6: Checking individual org slugs...';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    COUNT(*) as total_individual_orgs,
    COUNT(CASE WHEN slug LIKE 'user-%' THEN 1 END) as correct_pattern,
    CASE
        WHEN COUNT(*) = COUNT(CASE WHEN slug LIKE 'user-%' THEN 1 END)
        THEN '✅ PASS - All individual orgs follow user-xxx pattern'
        ELSE '❌ FAIL - Some orgs have incorrect slug pattern'
    END as test_result
FROM organizations
WHERE is_individual = true
AND is_active = true
AND slug != 'individuals';  -- Exclude old shared org

-- Expected: All individual orgs have slug starting with "user-"

-- ============================================
-- TEST 7: Test New Views
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 7: Testing individual_users_summary view...';
    RAISE NOTICE '==========================================';
END $$;

-- Check view exists and returns data
SELECT
    COUNT(*) as total_individual_users,
    SUM(keys_used) as total_keys,
    SUM(total_requests) as total_requests
FROM individual_users_summary;

-- Expected: At least 1 individual user

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Testing organization_summary view...';
END $$;

SELECT
    COUNT(*) as total_real_orgs
FROM organization_summary;

-- Expected: Only real organizations (no individuals)

-- Verify organization_summary excludes individuals
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM organization_summary
            WHERE slug LIKE 'user-%'
        )
        THEN '✅ PASS - organization_summary excludes individuals'
        ELSE '❌ FAIL - organization_summary includes individuals'
    END as test_result;

-- ============================================
-- TEST 8: Test Helper Functions
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 8: Testing helper functions...';
    RAISE NOTICE '==========================================';
END $$;

-- Test get_or_create_individual_org (idempotent - safe to run multiple times)
DO $$
DECLARE
    test_email TEXT := 'migration-test-user@example.com';
    org_id_1 UUID;
    org_id_2 UUID;
    test_result TEXT;
BEGIN
    -- First call: should create
    org_id_1 := get_or_create_individual_org(test_email, 'free');

    -- Second call: should return same org
    org_id_2 := get_or_create_individual_org(test_email, 'free');

    -- Verify
    IF org_id_1 = org_id_2 THEN
        test_result := '✅ PASS - get_or_create_individual_org is idempotent';
    ELSE
        test_result := '❌ FAIL - Function created duplicate org';
    END IF;

    RAISE NOTICE '%', test_result;

    -- Cleanup
    DELETE FROM organizations WHERE primary_contact_email = test_email;
END $$;

-- Test list_organizations_with_usage
DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Testing list_organizations_with_usage(false)...';
END $$;

SELECT
    COUNT(*) as org_count,
    CASE
        WHEN COUNT(*) = (SELECT COUNT(*) FROM organizations WHERE is_individual = false AND is_active = true)
        THEN '✅ PASS - Function excludes individuals by default'
        ELSE '❌ FAIL - Count mismatch'
    END as test_result
FROM list_organizations_with_usage(false);

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Testing list_organizations_with_usage(true)...';
END $$;

SELECT
    COUNT(*) as total_count,
    SUM(CASE WHEN is_individual THEN 1 ELSE 0 END) as individual_count
FROM list_organizations_with_usage(true);

-- Expected: total_count includes both types

-- ============================================
-- TEST 9: Verify Limit Enforcement
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 9: Testing limit enforcement...';
    RAISE NOTICE '==========================================';
END $$;

-- Check that each individual org has correct tier limits
SELECT
    o.slug,
    o.tier,
    COUNT(k.id) as current_keys,
    t.max_keys_per_email as limit,
    CASE
        WHEN COUNT(k.id) <= t.max_keys_per_email
        THEN '✅ Within limit'
        ELSE '❌ EXCEEDED LIMIT'
    END as status
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.is_individual = true
AND o.is_active = true
GROUP BY o.id, o.slug, o.tier, t.max_keys_per_email
ORDER BY current_keys DESC
LIMIT 10;

-- Expected: All should show "Within limit"

-- ============================================
-- TEST 10: Verify Data Integrity
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TEST 10: Data integrity checks...';
    RAISE NOTICE '==========================================';
END $$;

-- Check: All individual orgs have an email
SELECT
    COUNT(*) as orgs_without_email,
    CASE
        WHEN COUNT(*) = 0
        THEN '✅ PASS - All individual orgs have email'
        ELSE '❌ FAIL - Some individual orgs missing email'
    END as test_result
FROM organizations
WHERE is_individual = true
AND is_active = true
AND primary_contact_email IS NULL;

-- Expected: 0 orgs without email

-- Check: All real orgs have is_individual = false
SELECT
    COUNT(*) as misconfigured_orgs,
    CASE
        WHEN COUNT(*) = 0
        THEN '✅ PASS - All real orgs properly configured'
        ELSE '❌ FAIL - Some real orgs misconfigured'
    END as test_result
FROM organizations
WHERE is_active = true
AND slug NOT LIKE 'user-%'
AND slug != 'individuals'
AND is_individual = true;

-- Expected: 0 misconfigured orgs

-- ============================================
-- FINAL SUMMARY
-- ============================================

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'MIGRATION SUMMARY';
    RAISE NOTICE '==========================================';
END $$;

SELECT
    'Total Organizations' as metric,
    COUNT(*)::TEXT as value
FROM organizations
WHERE is_active = true

UNION ALL

SELECT
    'Individual Users',
    COUNT(*)::TEXT
FROM organizations
WHERE is_individual = true AND is_active = true

UNION ALL

SELECT
    'Real Organizations',
    COUNT(*)::TEXT
FROM organizations
WHERE is_individual = false AND is_active = true

UNION ALL

SELECT
    'Total Active API Keys',
    COUNT(*)::TEXT
FROM api_keys
WHERE is_active = true

UNION ALL

SELECT
    'Unique Emails',
    COUNT(DISTINCT email)::TEXT
FROM api_keys
WHERE email IS NOT NULL

UNION ALL

SELECT
    'Orphaned Keys',
    COUNT(*)::TEXT
FROM api_keys k
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o
    WHERE o.id = k.organization_id AND o.is_active = true
);

DO $$ BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'TESTS COMPLETE';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Review the output above for any FAIL messages.';
    RAISE NOTICE 'All tests should show ✅ PASS for successful migration.';
    RAISE NOTICE '==========================================';
END $$;
