# Testing Guide: Phase 3C - Notion-Style Individual Organizations

This guide will help you test the implementation via terminal to verify everything works correctly.

## Prerequisites

1. Ensure you have access to your Supabase database
2. Python environment with dependencies installed
3. `.env` file configured with Supabase credentials

## Step 1: Check Current State (Before Migration)

```bash
# Connect to your database
# Option A: Using psql
psql -h [your-supabase-host] -U postgres -d postgres

# Option B: Use Supabase SQL Editor in the dashboard
```

Run these queries to see current state:

```sql
-- Check organizations table structure
\d organizations

-- Count organizations
SELECT
    COUNT(*) as total_orgs,
    COUNT(CASE WHEN slug = 'individuals' THEN 1 END) as individuals_org
FROM organizations;

-- Check API keys in shared individuals org
SELECT
    COUNT(*) as total_keys,
    COUNT(DISTINCT email) as unique_emails
FROM api_keys
WHERE organization_id = '00000000-0000-0000-0000-000000000000';

-- Show sample keys from individuals org
SELECT id, client_name, email, organization, created_at
FROM api_keys
WHERE organization_id = '00000000-0000-0000-0000-000000000000'
LIMIT 5;
```

**Expected Results:**
- Organizations table exists without `is_individual` column
- Shared "individuals" org exists with UUID `00000000-...`
- Multiple API keys with different emails in the shared org

## Step 2: Run the Migrations

### First: Fix Type Mismatch (if not already done)

```bash
# From project root
psql -h [your-host] -U postgres -d postgres -f migrations/004b_fix_type_mismatch.sql
```

**Expected Output:**
```
CREATE OR REPLACE FUNCTION
CREATE OR REPLACE FUNCTION
DROP VIEW
CREATE VIEW
Type mismatch fixed!
```

### Second: Run Individual Organizations Migration

```bash
# From project root
psql -h [your-host] -U postgres -d postgres -f migrations/005_split_individuals_into_separate_orgs.sql
```

**Expected Output:**
```
ALTER TABLE
CREATE INDEX
COMMENT
Starting migration: Splitting shared individuals org...
Processing user: john@example.com
  Created personal org: user-a1b2c3d4e5f6 (id: ...)
  Migrated keys for john@example.com
Processing user: jane@example.com
  Created personal org: user-b2c3d4e5f6g7 (id: ...)
  Migrated keys for jane@example.com
...
Migration complete! Shared individuals org marked as inactive.
DROP VIEW
CREATE VIEW
CREATE VIEW
CREATE OR REPLACE FUNCTION
CREATE OR REPLACE FUNCTION
CREATE OR REPLACE FUNCTION
================================
Migration Summary:
  Real Organizations: 2
  Individual Users: 15
  Orphaned Keys: 0
================================
```

## Step 3: Verify Migration Results

### Check Organizations Table

```sql
-- Verify is_individual column was added
\d organizations

-- Count organizations by type
SELECT
    is_individual,
    COUNT(*) as count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count
FROM organizations
GROUP BY is_individual;

-- List individual organizations
SELECT id, name, slug, tier, primary_contact_email, is_active
FROM organizations
WHERE is_individual = true
ORDER BY created_at DESC
LIMIT 10;

-- List real organizations
SELECT id, name, slug, tier, primary_contact_email, is_active
FROM organizations
WHERE is_individual = false
ORDER BY created_at DESC;
```

**Expected Results:**
- `is_individual` column exists (boolean)
- Multiple individual orgs (one per unique email)
- Real orgs have `is_individual = false`
- Old shared org is marked `is_active = false`

### Check API Keys Migration

```sql
-- Check that keys were migrated properly
SELECT
    COUNT(*) as total_keys,
    COUNT(DISTINCT organization_id) as unique_orgs
FROM api_keys
WHERE organization_id != '00000000-0000-0000-0000-000000000000';

-- Verify each email has their own organization
SELECT
    k.email,
    o.slug,
    o.is_individual,
    COUNT(k.id) as key_count
FROM api_keys k
JOIN organizations o ON o.id = k.organization_id
WHERE k.email IS NOT NULL
AND o.is_active = true
GROUP BY k.email, o.slug, o.is_individual
ORDER BY key_count DESC;

-- Check for orphaned keys (should be 0)
SELECT COUNT(*) as orphaned_keys
FROM api_keys k
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o
    WHERE o.id = k.organization_id
    AND o.is_active = true
);
```

**Expected Results:**
- All keys moved out of shared org
- Each unique email has their own organization
- Zero orphaned keys

### Test New Views

```sql
-- View individual users (admin view)
SELECT * FROM individual_users_summary
ORDER BY total_requests DESC
LIMIT 10;

-- View real organizations (public view)
SELECT * FROM organization_summary
ORDER BY total_requests DESC;

-- Test the list function (exclude individuals by default)
SELECT * FROM list_organizations_with_usage(false);

-- Test the list function (include individuals)
SELECT * FROM list_organizations_with_usage(true)
WHERE is_individual = true;
```

**Expected Results:**
- `individual_users_summary` shows individual users only
- `organization_summary` shows real orgs only (excludes individuals)
- Function works with both true/false parameters

## Step 4: Test Python CLI

### Test Creating Keys for Individuals

```bash
# Create a key for an individual user (no --organization flag)
python manage_api_keys.py create \
    --name "Test Individual Key" \
    --email "testuser@example.com" \
    --tier "free" \
    --description "Testing individual org creation"
```

**Expected Output:**
```
✅ Success
API Key Created Successfully!

⚠️  IMPORTANT: Save this key now - it cannot be retrieved later!

API Key: [long-key-string]
Client: Test Individual Key
ID: [uuid]
Expires: Never
Rate Limits: 60/min, 1000/hour, 10000/day
```

**Verify in Database:**
```sql
-- Check that a personal org was created
SELECT
    o.id, o.slug, o.is_individual, o.primary_contact_email,
    k.client_name, k.key_prefix
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE o.primary_contact_email = 'testuser@example.com';
```

**Expected:**
- New org with slug like `user-a1b2c3d4e5f6`
- `is_individual = true`
- API key linked to this personal org

### Test Creating Keys for Organizations

```bash
# Create a key for a real organization
python manage_api_keys.py create \
    --name "Acme Corp Production" \
    --email "admin@acme.com" \
    --organization "Acme Corp" \
    --tier "pro" \
    --description "Testing real org creation"
```

**Expected Output:**
```
✅ Success
[API key details...]
```

**Verify in Database:**
```sql
-- Check that a real org was created
SELECT
    o.id, o.name, o.slug, o.is_individual,
    k.client_name, k.key_prefix
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE o.slug = 'acme-corp';
```

**Expected:**
- New org with slug `acme-corp`
- `is_individual = false`
- Name is "Acme Corp" (user-friendly)

### Test Listing Organizations

```bash
# List all organizations (should exclude individuals)
python manage_api_keys.py list-orgs
```

**Expected Output:**
```
Organizations

┌────────────┬──────────┬──────┬──────────┬────────────┬───────┬──────────┬────────┐
│ Name       │ Slug     │ Tier │ Keys ... │ Keys Limit │ Users │ Requests │ Status │
├────────────┼──────────┼──────┼──────────┼────────────┼───────┼──────────┼────────┤
│ Acme Corp  │ acme-... │ PRO  │ 1        │ 10         │ 1     │ 0        │ 🟢 ... │
└────────────┴──────────┴──────┴──────────┴────────────┴───────┴──────────┴────────┘
```

**Should NOT show:**
- Individual personal orgs (user-xxx)
- The old shared "individuals" org

### Test Limit Enforcement

```bash
# Try to create 3 keys for the same individual (should fail on 3rd)
python manage_api_keys.py create --name "Key 1" --email "limittest@example.com" --tier "free"
python manage_api_keys.py create --name "Key 2" --email "limittest@example.com" --tier "free"
python manage_api_keys.py create --name "Key 3" --email "limittest@example.com" --tier "free"
```

**Expected Results:**
- First 2 keys: Success ✅
- Third key: Error ❌
  ```
  Error creating API key: Organization "Personal - limittest@example.com"
  has reached maximum of 2 API keys for free tier
  ```

**Verify in Database:**
```sql
-- Check keys for this user
SELECT o.slug, o.tier, COUNT(k.id) as key_count
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE o.primary_contact_email = 'limittest@example.com'
GROUP BY o.slug, o.tier;
```

**Expected:**
- Exactly 2 active keys
- Organization has free tier (limit of 2)

## Step 5: Test Helper Functions

### Test get_or_create_individual_org()

```sql
-- Should return existing org for known email
SELECT get_or_create_individual_org('testuser@example.com', 'free');

-- Should create new org for new email
SELECT get_or_create_individual_org('newuser@example.com', 'pro');

-- Verify both calls
SELECT slug, tier, is_individual, primary_contact_email
FROM organizations
WHERE primary_contact_email IN ('testuser@example.com', 'newuser@example.com');
```

**Expected:**
- First call returns existing org ID
- Second call creates new org and returns its ID
- Both orgs have `is_individual = true`

### Test get_user_organization()

```sql
-- Get a user's organization (for UI routing)
SELECT * FROM get_user_organization('testuser@example.com');
```

**Expected Output:**
```
 id | name | slug | tier | is_individual | is_active
----+------+------+------+---------------+-----------
 ...| Personal - testuser@... | user-... | free | true | true
```

## Step 6: Test Edge Cases

### Test Keywords for Individual Orgs

```bash
# These should all create individual orgs (not real orgs)
python manage_api_keys.py create --name "Test" --email "test1@example.com" --organization "individual"
python manage_api_keys.py create --name "Test" --email "test2@example.com" --organization "individuals"
python manage_api_keys.py create --name "Test" --email "test3@example.com" --organization "personal"
python manage_api_keys.py create --name "Test" --email "test4@example.com" --organization "solo"
```

**Verify:**
```sql
SELECT o.slug, o.is_individual, k.organization
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE k.email IN ('test1@example.com', 'test2@example.com', 'test3@example.com', 'test4@example.com');
```

**Expected:**
- All have `is_individual = true`
- All have personal org slugs (user-xxx)

### Test Without Email (Should Fail)

```bash
# Try to create individual key without email
python manage_api_keys.py create --name "Test" --tier "free"
```

**Expected:**
```
Error: Email is required when no organization is specified
```

## Step 7: Cleanup Test Data (Optional)

```sql
-- Remove test users
DELETE FROM api_keys
WHERE email IN ('testuser@example.com', 'newuser@example.com', 'limittest@example.com');

DELETE FROM organizations
WHERE primary_contact_email IN ('testuser@example.com', 'newuser@example.com', 'limittest@example.com');
```

## ✅ Success Criteria

Your implementation is working correctly if:

- ✅ `is_individual` column exists on organizations table
- ✅ All unique emails have their own personal organization
- ✅ Personal orgs have `is_individual = true`
- ✅ Real orgs have `is_individual = false`
- ✅ Old shared "individuals" org is inactive
- ✅ Zero orphaned keys
- ✅ Views exclude individual orgs from public display
- ✅ Creating keys without `--organization` creates personal orgs
- ✅ Creating keys with `--organization` creates real orgs
- ✅ Limit enforcement works per organization (not shared!)
- ✅ `list-orgs` command excludes personal orgs
- ✅ All helper functions work correctly

## 🐛 Troubleshooting

### Issue: Migration fails with "column already exists"

**Solution:** The migration has already been run. Check:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'organizations' AND column_name = 'is_individual';
```

### Issue: Keys still in shared org

**Solution:** Re-run migration or manually migrate:
```sql
-- Check if migration completed
SELECT is_active FROM organizations
WHERE id = '00000000-0000-0000-0000-000000000000';
-- Should be false
```

### Issue: Limit not working (multiple users sharing limit)

**Solution:** Verify each user has their own org:
```sql
SELECT email, organization_id, COUNT(*)
FROM api_keys
WHERE email IS NOT NULL
GROUP BY email, organization_id
HAVING COUNT(DISTINCT organization_id) > 1;
-- Should return 0 rows
```

## 📊 Monitoring Queries (Production)

```sql
-- Count of individual vs real organizations
SELECT
    CASE WHEN is_individual THEN 'Individual' ELSE 'Organization' END as type,
    COUNT(*) as count,
    SUM((SELECT COUNT(*) FROM api_keys WHERE organization_id = organizations.id)) as total_keys
FROM organizations
WHERE is_active = true
GROUP BY is_individual;

-- Top individual users by usage
SELECT * FROM individual_users_summary
ORDER BY total_requests DESC
LIMIT 20;

-- Top real organizations by usage
SELECT * FROM organization_summary
ORDER BY total_requests DESC
LIMIT 20;

-- Health check: No orphaned keys
SELECT
    CASE WHEN COUNT(*) = 0 THEN '✅ PASS' ELSE '❌ FAIL' END as status,
    COUNT(*) as orphaned_keys
FROM api_keys k
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o
    WHERE o.id = k.organization_id AND o.is_active = true
);
```
