# Troubleshooting: PostgreSQL digest() Function Type Casting Issue

## Problem Summary

The `get_or_create_individual_org()` function is failing with type casting errors when calling the `digest()` function from the pgcrypto extension. PostgreSQL is not automatically casting the parameters to the correct types.

**Error Evolution:**
1. ❌ `function digest(bytea, text) does not exist` - Extension not enabled
2. ❌ `function digest(text, unknown) does not exist` - First param needs casting
3. ❌ `function digest(bytea, unknown) does not exist` - Second param needs casting

**Root Cause:** The `digest()` function signature is `digest(data bytea, type text)`, but PostgreSQL requires explicit type casts in some configurations.

---

## Phase 1: Verify pgcrypto Extension

### Tasks

- [x] Check if pgcrypto extension is installed
  ```sql
  SELECT * FROM pg_extension WHERE extname = 'pgcrypto';
  ```
- [x] Verify extension version (should be 1.3 or higher)

**Status:** ✅ Extension is installed (version 1.3)

---

## Phase 2: Test digest() Function Directly

### Tasks

- [ ] **Test digest() with explicit casts in Supabase SQL Editor**
  ```sql
  -- Test 1: Both parameters explicitly cast
  SELECT encode(digest('test@example.com'::bytea, 'sha256'::text), 'hex');

  -- Test 2: Only first parameter cast
  SELECT encode(digest('test@example.com'::bytea, 'sha256'), 'hex');

  -- Test 3: No casts (to confirm it fails)
  SELECT encode(digest('test@example.com', 'sha256'), 'hex');
  ```

- [ ] **Record which test succeeds**
  - If Test 1 succeeds: Need both `::bytea` and `::text` casts
  - If Test 2 succeeds: Need only `::bytea` cast
  - If all fail: Check pgcrypto installation

- [ ] **Generate expected hash for 'user@example.com'**
  ```sql
  SELECT 'user-' || substring(
      encode(digest('user@example.com'::bytea, 'sha256'::text), 'hex'),
      1, 16
  ) as expected_slug;
  ```

**Expected Result:** Should return a slug like `user-b4c9a289323b21a0`

---

## Phase 3: Fix Migration File

Based on Phase 2 results, update the migration file with correct type casts.

### Tasks

- [ ] **Fix Line 50 (DO block migration logic)**

  Current code:
  ```sql
  user_slug := 'user-' || substring(
      encode(digest(key_record.email::bytea, 'sha256'), 'hex'),
      1, 16
  );
  ```

  Fixed code:
  ```sql
  user_slug := 'user-' || substring(
      encode(digest(key_record.email::bytea, 'sha256'::text), 'hex'),
      1, 16
  );
  ```

- [ ] **Fix Line 205 (get_or_create_individual_org function)**

  Current code:
  ```sql
  user_slug := 'user-' || substring(
      encode(digest(user_email::bytea, 'sha256'), 'hex'),
      1, 16
  );
  ```

  Fixed code:
  ```sql
  user_slug := 'user-' || substring(
      encode(digest(user_email::bytea, 'sha256'::text), 'hex'),
      1, 16
  );
  ```

- [ ] **Save the updated migration file**

---

## Phase 4: Create Quick Fix SQL Script

Create a standalone SQL script to update only the function (without re-running the entire migration).

### Tasks

- [ ] **Create file: `migrations/005b_fix_digest_type_casting.sql`**
  ```sql
  -- Fix: Add explicit type casts to digest() function calls
  -- Date: 2025-12-10
  -- Fixes: "function digest(bytea, unknown) does not exist" error

  -- Drop and recreate the function with proper type casts
  DROP FUNCTION IF EXISTS get_or_create_individual_org(TEXT, TEXT);

  CREATE OR REPLACE FUNCTION get_or_create_individual_org(
      user_email TEXT,
      user_tier TEXT DEFAULT 'free'
  )
  RETURNS UUID AS $$
  DECLARE
      org_id UUID;
      user_slug TEXT;
  BEGIN
      -- Generate slug from email (with explicit type casts)
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

  COMMENT ON FUNCTION get_or_create_individual_org IS 'Get or create a personal organization for an individual user (with explicit type casts)';
  ```

- [ ] **Save the quick fix file**

---

## Phase 5: Apply the Fix

Choose ONE of these approaches:

### Option A: Re-run Full Migration (Recommended)

- [ ] **Copy updated `005_split_individuals_into_separate_orgs.sql`**
- [ ] **Paste into Supabase SQL Editor**
- [ ] **Click "Run"**
- [ ] **Verify no errors in output**

### Option B: Run Quick Fix Only (Faster)

- [ ] **Copy `005b_fix_digest_type_casting.sql`**
- [ ] **Paste into Supabase SQL Editor**
- [ ] **Click "Run"**
- [ ] **Verify "CREATE FUNCTION" success message**

---

## Phase 6: Verify the Fix

### Tasks

- [ ] **Test the function directly in Supabase**
  ```sql
  -- Should return a UUID
  SELECT get_or_create_individual_org('test@example.com', 'free');
  ```

- [ ] **Verify organization was created**
  ```sql
  SELECT o.id, o.slug, o.is_individual, o.primary_contact_email
  FROM organizations o
  WHERE primary_contact_email = 'test@example.com';
  ```

  Expected:
  - `slug` starts with `user-`
  - `is_individual` = `true`
  - `primary_contact_email` = `test@example.com`

- [ ] **Check function exists with correct signature**
  ```sql
  SELECT routine_name, routine_type
  FROM information_schema.routines
  WHERE routine_name = 'get_or_create_individual_org';
  ```

---

## Phase 7: Test API Key Creation

### Tasks

- [ ] **Create API key using Python CLI**
  ```bash
  python manage_api_keys.py create --name "Test Key" --email "user@example.com" --tier "free"
  ```

- [ ] **Verify success message and API key returned**

- [ ] **List API keys to confirm**
  ```bash
  python manage_api_keys.py list
  ```

- [ ] **Verify in database**
  ```sql
  SELECT
      k.id,
      k.client_name,
      k.email,
      o.slug as org_slug,
      o.is_individual
  FROM api_keys k
  JOIN organizations o ON o.id = k.organization_id
  WHERE k.email = 'user@example.com';
  ```

- [ ] **Clean up test data**
  ```bash
  python manage_api_keys.py revoke "user@example.com"
  ```

---

## Phase 8: Update Documentation

### Tasks

- [ ] **Update `action-required.md`**
  - Mark Phase 3C migration as complete
  - Note the type casting issue encountered
  - Add troubleshooting note for future reference

- [ ] **Add note to migration file**
  ```sql
  -- NOTE: Some PostgreSQL configurations require explicit type casts
  -- for the digest() function. If you encounter errors, ensure both
  -- parameters are cast: digest(text::bytea, 'sha256'::text)
  ```

- [ ] **Document the fix in `PHASE3C_ORGANIZATION_LIMITS.md`**

---

## Alternative Solutions (If Above Fails)

### If Type Casting Still Doesn't Work

- [ ] **Check PostgreSQL version**
  ```sql
  SELECT version();
  ```
  - Minimum required: PostgreSQL 10+
  - Recommended: PostgreSQL 13+

- [ ] **Verify pgcrypto is in search path**
  ```sql
  SHOW search_path;
  -- Should include 'public' or the schema where pgcrypto is installed
  ```

- [ ] **Try alternate hash approach (without digest)**
  ```sql
  -- Use md5 instead (built-in, no extension needed)
  user_slug := 'user-' || substring(md5(user_email), 1, 16);
  ```

- [ ] **Check Supabase-specific settings**
  - Verify PostgREST can access pgcrypto functions
  - Check RLS policies don't block function execution

---

## Success Criteria

✅ All phases completed when:
- [ ] pgcrypto extension is enabled
- [ ] `digest()` function works with test queries
- [ ] `get_or_create_individual_org()` function executes without errors
- [ ] API keys can be created via Python CLI
- [ ] Personal organizations are auto-created with correct slugs
- [ ] Database queries confirm proper structure

---

## Common Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `function digest(bytea, text) does not exist` | pgcrypto not enabled | Run `CREATE EXTENSION IF NOT EXISTS pgcrypto;` |
| `function digest(text, unknown) does not exist` | First param needs cast | Use `email::bytea` |
| `function digest(bytea, unknown) does not exist` | Second param needs cast | Use `'sha256'::text` |
| `permission denied for function digest` | RLS policy issue | Use service role key or adjust policies |
| `null value in column "slug"` | digest() returning null | Check input email is not null |

---

## Next Steps After Fix

Once the digest function is working:

1. Create production API keys for actual users
2. Test tier-based limits (free: 2 keys, pro: 10 keys)
3. Test organization creation for real companies
4. Run comprehensive test suite (`TEST_005_verify_migration.sql`)
5. Deploy to production

---

## Support & References

- **Migration File:** `migrations/005_split_individuals_into_separate_orgs.sql`
- **Quick Fix:** `migrations/005b_fix_digest_type_casting.sql` (to be created)
- **Test Script:** `migrations/TEST_005_verify_migration.sql`
- **Documentation:** `specs/api-key-authentication/PHASE3C_ORGANIZATION_LIMITS.md`
- **pgcrypto Docs:** https://www.postgresql.org/docs/current/pgcrypto.html

---

*Last Updated: 2025-12-10*
