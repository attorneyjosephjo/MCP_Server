# Action Required: API Key Authentication

Manual steps that must be completed by a human. These cannot be automated.

## Phase 1 (Environment Variables) - ✅ COMPLETE

### Before Implementation

- [x] **Review security requirements** - Ensure HTTPS is enabled on Coolify deployment for production

### During Implementation

- [x] **Generate API keys** - Run `python -c "import secrets; print(secrets.token_urlsafe(32))"` to create 2-3 secure keys
- [x] **Update .env file** - Add generated API keys to `.env` file (never commit this file!)
- [x] **Configure environment variables in Coolify** - Set `MCP_API_AUTH_ENABLED=true` and `MCP_API_KEYS` in deployment platform
- [x] **Verify HTTPS is enabled** - Check Coolify SSL/TLS settings to ensure API keys are transmitted securely over HTTPS

### After Implementation

- [x] **Test with real clients** - Provide API keys to initial clients and verify they can connect successfully
- [x] **Monitor logs** - Check server logs for authentication events and any issues

## Phase 2 (Database-Backed) - ⏳ READY FOR TESTING

### Prerequisites

- [x] **Verify Supabase connection** - Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set in `.env`
- [x] **Review database migration** - Read `migrations/001_create_api_keys_tables.sql` to understand what will be created

### Database Setup

- [x] **Run database migration** - Execute `migrations/001_create_api_keys_tables.sql` in Supabase SQL Editor
- [x] **Verify tables created** - Run query: `SELECT table_name FROM information_schema.tables WHERE table_name IN ('api_keys', 'api_key_usage');`
- [x] **Verify indexes created** - Run query: `SELECT indexname FROM pg_indexes WHERE tablename IN ('api_keys', 'api_key_usage');`
- [x] **Test helper functions** - Run query: `SELECT deactivate_expired_api_keys();` (should return 0)

### API Key Creation

- [x] **Create first API key** - Run: `python manage_api_keys.py create --name "Production Client"`
- [x] **Save API key securely** - Copy the key immediately (cannot be retrieved later!)
- [x] **Create test key** - Run: `python manage_api_keys.py create --name "Test Client" --expires 30`
- [x] **Verify keys in database** - Run: `python manage_api_keys.py list`

### Enable Database Mode

- [x] **Update .env file** - Set `MCP_API_AUTH_DB_ENABLED=true`
- [x] **Update Coolify environment** - Add `MCP_API_AUTH_DB_ENABLED=true` to deployment platform

### Testing

- [ ] **Test authentication with valid key** - `curl -H "Authorization: Bearer <key>" http://localhost:3000/mcp/v1/initialize`
- [ ] **Test authentication with invalid key** - Should return 401 Unauthorized
- [ ] **Test authentication without key** - Should return 401 with clear error message
- [ ] **Test rate limiting** - Make 61+ requests in 1 minute, should get 429 after 60
- [ ] **Test usage logging** - Check database: `SELECT * FROM api_key_usage ORDER BY timestamp DESC LIMIT 10;`
- [ ] **Test usage statistics** - Run: `python manage_api_keys.py usage "Production Client" --days 7`
- [ ] **Test key rotation** - Run: `python manage_api_keys.py rotate "Test Client"`
- [ ] **Test key revocation** - Run: `python manage_api_keys.py revoke "Test Client"`, verify 401 on next request

### Deployment

- [ ] **Deploy to staging** - Test in staging environment first
- [ ] **Monitor logs** - Check for errors: `tail -f legal_rag_server.log`
- [ ] **Verify database connections** - Check Supabase logs for connection issues
- [ ] **Deploy to production** - Deploy with database mode enabled
- [ ] **Verify production deployment** - Test with production API keys

### Migration from Phase 1 to Phase 2

- [ ] **Document existing clients** - List all clients currently using environment variable keys
- [ ] **Create database keys for existing clients** - Use `manage_api_keys.py create` for each client
- [ ] **Notify clients of key change** - Provide new database-backed API keys
- [ ] **Set migration deadline** - Give clients time to migrate (e.g., 30 days)
- [ ] **Switch to database mode** - Set `MCP_API_AUTH_DB_ENABLED=true`
- [ ] **Monitor for issues** - Watch for authentication failures during migration
- [ ] **Remove environment keys** - After migration complete, remove `MCP_API_KEYS` from `.env`

### Post-Deployment

- [ ] **Document API keys for clients** - Provide clients with their API keys and usage instructions
- [ ] **Set up monitoring** - Monitor usage patterns and rate limit violations
- [ ] **Schedule key rotation** - Plan to rotate keys periodically (e.g., every 90 days)
- [ ] **Set up cleanup job** - Schedule periodic cleanup: `python manage_api_keys.py cleanup --days 90`
- [ ] **Archive old usage data** - Plan monthly cleanup of old `api_key_usage` records (keep 90 days)

## Phase 3A (Email-Based User Management) - ✅ IMPLEMENTED

### Database Migration

- [x] **Run Phase 3A migration** - Execute `migrations/002_add_email_to_api_keys.sql` in Supabase SQL Editor
- [x] **Verify columns added** - Run: `SELECT column_name FROM information_schema.columns WHERE table_name = 'api_keys' AND column_name IN ('email', 'organization');`
- [x] **Test unique constraint** - Try creating two keys with same email, second should fail
- [x] **Test helper functions** - Run: `SELECT * FROM get_keys_by_email('test@example.com');`

### Update Existing Keys

- [ ] **Add email to existing keys** - Run SQL: `UPDATE api_keys SET email = 'admin@thejolawfirm.com', organization = 'The Jo Law Firm' WHERE email IS NULL;`
- [ ] **Verify update** - Run: `SELECT id, client_name, email, organization FROM api_keys;`

### Create New Keys with Email

- [x] **Create production key** - Run: `python manage_api_keys.py create --name "Joseph Jo" --email "joseph.jo@thejolawfirm.com" --organization "The Jo Law Firm"`
- [x] **Create test key** - Run: `python manage_api_keys.py create --name "Test" --email "test@moohan.com" --organization "Moohan, Inc."`
- [x] **List keys** - Run: `python manage_api_keys.py list` (should show email and organization columns)

### Testing

- [ ] **Test duplicate email prevention** - Try creating key with same email, should get error "Maximum 10 active API keys per email address" after 10 keys
- [ ] **Test organization queries** - Run: `SELECT * FROM get_organization_stats('The Jo Law Firm');`
- [ ] **Test multiple keys per user** - Create 2-3 keys with same email, verify all show up
- [ ] **Verify email format validation** - Try creating key with invalid email (e.g., "notanemail"), should fail

### Documentation

- [ ] **Update team on new fields** - Notify team that new keys should include `--email` and `--organization`
- [ ] **Document email policy** - Decide: one email per person, or one email per service?
- [ ] **Update client onboarding** - Add email/org collection to new client setup process

## Phase 3C (Notion-Style Individual Organizations) - ⏳ READY FOR DEPLOYMENT

### Prerequisites

- [x] **Review migration file** - Read `migrations/005_split_individuals_into_separate_orgs.sql` to understand what will change
- [x] **Understand the problem** - All individuals currently share one organization, breaking per-user limits
- [x] **Backup database** - Create a backup before running migration (recommended)

### Database Migration

- [ ] **Run Phase 3C migration** - Execute `migrations/005_split_individuals_into_separate_orgs.sql` in Supabase SQL Editor
  ```sql
  -- Copy and paste the entire file into Supabase SQL Editor and click "Run"
  ```
- [ ] **If you encounter digest() type casting errors** - Run the quick fix:
  ```sql
  -- If you see: "function digest(bytea, unknown) does not exist"
  -- Execute: migrations/005b_fix_digest_type_casting.sql
  ```
  - **Troubleshooting guide**: See `TROUBLESHOOTING_DIGEST_FUNCTION.md` for detailed diagnosis
  - **Test scripts**: Use `PHASE2_test_digest_function.sql` and `PHASE6_verify_fix.sql`
  - **Root cause**: Some PostgreSQL configurations require explicit type casts for both `digest()` parameters
  - **Fix**: Already applied in migration files (`::bytea` and `'sha256'::text` casts)
- [ ] **Watch migration output** - Should show:
  - "Starting migration: Splitting shared individuals org..."
  - "Processing user: [email]" for each user
  - "Migration complete! Shared individuals org marked as inactive."
  - Migration summary with counts
- [ ] **Verify is_individual column added** - Run:
  ```sql
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'organizations' AND column_name = 'is_individual';
  ```
- [ ] **Check migration summary** - Note the counts of:
  - Real Organizations
  - Individual Users
  - Orphaned Keys (should be 0)

### Verification Tests

- [ ] **Run comprehensive test script** - Execute `migrations/TEST_005_verify_migration.sql` in Supabase:
  ```sql
  -- Copy and paste TEST_005_verify_migration.sql into Supabase SQL Editor
  -- This will run 10 automated tests
  ```
- [ ] **Review test results** - All tests should show "✅ PASS"
- [ ] **Check for FAIL messages** - If any test shows "❌ FAIL", review the issue before proceeding

### Manual Verification Queries

Run these queries to manually verify the migration:

```sql
-- 1. Count organizations by type
SELECT
    CASE WHEN is_individual THEN 'Individual' ELSE 'Organization' END as type,
    COUNT(*) as count
FROM organizations
WHERE is_active = true
GROUP BY is_individual;

-- 2. Verify each email has their own org
SELECT
    o.primary_contact_email,
    o.slug,
    o.is_individual,
    COUNT(k.id) as key_count
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
WHERE o.is_individual = true
AND o.is_active = true
GROUP BY o.id, o.primary_contact_email, o.slug, o.is_individual
ORDER BY key_count DESC
LIMIT 10;

-- 3. Verify old shared org is inactive
SELECT id, slug, is_active
FROM organizations
WHERE id = '00000000-0000-0000-0000-000000000000';
-- Should show: is_active = false

-- 4. Check for orphaned keys (should be 0)
SELECT COUNT(*) as orphaned_keys
FROM api_keys k
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o
    WHERE o.id = k.organization_id AND o.is_active = true
);
```

### Test New Functionality

Test that the new individual organization creation works:

```bash
# 1. Create key for individual user (auto-creates personal org)
python manage_api_keys.py create \
    --name "Test Individual" \
    --email "testuser@example.com" \
    --tier "free"

# 2. Verify personal org was created
# Run SQL query:
SELECT o.slug, o.is_individual, k.client_name
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE o.primary_contact_email = 'testuser@example.com';
# Should show: slug like "user-xxx", is_individual = true

# 3. Create key for real organization
python manage_api_keys.py create \
    --name "Acme Corp Key" \
    --email "admin@acme.com" \
    --organization "Acme Corp" \
    --tier "pro"

# 4. Verify real org was created
# Run SQL query:
SELECT o.slug, o.is_individual, k.client_name
FROM organizations o
JOIN api_keys k ON k.organization_id = o.id
WHERE o.slug = 'acme-corp';
# Should show: slug = "acme-corp", is_individual = false

# 5. List organizations (should exclude individuals)
python manage_api_keys.py list-orgs
# Should show: Only real orgs like "Acme Corp", NOT personal orgs
```

### Test Limit Enforcement

Verify that per-individual limits now work correctly:

```bash
# 1. Create 2 keys for a test user (free tier = 2 max)
python manage_api_keys.py create --name "Key 1" --email "limit-test@example.com" --tier "free"
python manage_api_keys.py create --name "Key 2" --email "limit-test@example.com" --tier "free"

# 2. Try to create 3rd key (should fail)
python manage_api_keys.py create --name "Key 3" --email "limit-test@example.com" --tier "free"
# Expected error: "Organization has reached maximum of 2 API keys for free tier"

# 3. Verify another user is NOT affected
python manage_api_keys.py create --name "Different User" --email "another@example.com" --tier "free"
# Should succeed ✅ (each individual has their own limit)
```

### Post-Migration Cleanup

```bash
# Remove test users created during verification
python manage_api_keys.py revoke "testuser@example.com"
python manage_api_keys.py revoke "limit-test@example.com"
python manage_api_keys.py revoke "another@example.com"
```

### Known Changes & Impact

**What Changed:**
- ✅ Each individual user now has their own organization
- ✅ Organization slugs follow pattern: `user-{hash}` for individuals
- ✅ Old shared "individuals" org is marked inactive (preserved for history)
- ✅ All existing API keys continue to work without interruption
- ✅ New `is_individual` boolean column added to organizations table

**Impact:**
- ✅ **Limits now work correctly** - Each individual has their own 2-key limit (not shared!)
- ✅ **Can upgrade individuals** - Can upgrade "john@example.com" to pro without affecting others
- ✅ **Better analytics** - Can track individual vs organization usage separately
- ✅ **Ready for UI** - Frontend can show/hide org features based on `is_individual`
- ✅ **Zero downtime** - All existing keys continue working during and after migration

**What Didn't Change:**
- ✅ No API changes - All authentication endpoints work the same
- ✅ No client updates needed - Existing API keys don't need to be regenerated
- ✅ Backward compatible - Python CLI handles both old and new patterns

### Rollback Plan

If issues occur, you can rollback:

```sql
-- Emergency rollback (reactivate shared org)
UPDATE organizations
SET is_active = true
WHERE id = '00000000-0000-0000-0000-000000000000';

-- Move all keys back to shared org (use with caution!)
UPDATE api_keys
SET organization_id = '00000000-0000-0000-0000-000000000000'
WHERE organization_id IN (
    SELECT id FROM organizations WHERE is_individual = true
);

-- Deactivate individual orgs
UPDATE organizations
SET is_active = false
WHERE is_individual = true;
```

**Note:** Rollback should only be used in emergency. Test thoroughly before rolling back.

### Documentation Updates

- [x] **Updated implementation-plan.md** - Added Phase 3C section with full details
- [x] **Created TESTING_GUIDE.md** - Comprehensive testing instructions
- [x] **Created TEST_005_verify_migration.sql** - Automated test script
- [ ] **Update team on changes** - Notify team about new individual organization behavior
- [ ] **Update frontend plans** - Plan UI to conditionally show org features based on `is_individual`

### Success Criteria

Migration is successful when:
- ✅ All tests in `TEST_005_verify_migration.sql` show PASS
- ✅ Each unique email has their own organization
- ✅ Individual orgs have `is_individual = true`
- ✅ Real orgs have `is_individual = false`
- ✅ Old shared org is inactive
- ✅ Zero orphaned keys
- ✅ New individual keys auto-create personal orgs
- ✅ New organization keys create real orgs
- ✅ Limit enforcement works per-individual (not shared)
- ✅ `list-orgs` excludes personal orgs from display

## Security Checklist

### General Security

- [x] **HTTPS enabled** - API keys MUST be transmitted over HTTPS in production (never HTTP!)
- [x] **.env in .gitignore** - Verify `.env` file is not tracked by git (run `git status` to confirm)
- [x] **API keys are secret** - Do not share keys in chat, email, documentation, or logs
- [x] **Key length is secure** - Generated keys are 32+ bytes (token_urlsafe(32) provides this)

### Phase 1 Security (Environment Variables)

- [x] **Constant-time comparison** - Keys validated using `secrets.compare_digest()` to prevent timing attacks
- [x] **No keys in logs** - Verified API keys never appear in application logs
- [x] **Environment variables secured** - Coolify environment variables are encrypted at rest

### Phase 2 Security (Database-Backed)

- [ ] **Keys hashed in database** - Verify keys stored as SHA-256 hashes, never plaintext
- [ ] **Row Level Security enabled** - Verify RLS policies active on `api_keys` and `api_key_usage` tables
- [ ] **Service role key secured** - `SUPABASE_SERVICE_ROLE_KEY` stored securely and never exposed
- [ ] **Database backups encrypted** - Verify Supabase backups are encrypted
- [ ] **Rate limiting active** - Verify rate limits prevent abuse
- [ ] **Audit logging enabled** - All API requests logged to `api_key_usage` table
- [ ] **Key rotation schedule** - Plan established for regular key rotation (every 90 days)
- [ ] **Expired keys deactivated** - Schedule periodic runs of `deactivate_expired_api_keys()`
- [ ] **Monitor failed attempts** - Watch for repeated 401/429 errors (potential attacks)
- [ ] **Client IP logging** - Verify IP addresses logged for forensics

## Quick Start Guide

### Phase 1 (Simple - Good for 2-10 clients)

1. Generate keys: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Add to `.env`: `MCP_API_AUTH_ENABLED=true` and `MCP_API_KEYS=key1,key2`
3. Start server: `python legal_rag_server.py --http`
4. Test: `curl -H "Authorization: Bearer <key>" http://localhost:3000/`

### Phase 2 (Scalable - Unlimited clients)

1. Run migration in Supabase SQL Editor
2. Create key: `python manage_api_keys.py create --name "Client Name"`
3. Enable DB mode: Add `MCP_API_AUTH_DB_ENABLED=true` to `.env`
4. Start server: `python legal_rag_server.py --http`
5. Monitor usage: `python manage_api_keys.py usage "Client Name"`

### Phase 3A (Email-Based User Management)

1. Run migration: Execute `migrations/002_add_email_to_api_keys.sql` in Supabase
2. Create key with email: `python manage_api_keys.py create --name "Production" --email "user@example.com" --organization "Law Firm"`
3. List keys: `python manage_api_keys.py list` (shows email/org columns)
4. Query by email: `SELECT * FROM get_keys_by_email('user@example.com');`

### Phase 3C (Notion-Style Individual Organizations)

1. Run migration: Execute `migrations/005_split_individuals_into_separate_orgs.sql` in Supabase
2. Run tests: Execute `migrations/TEST_005_verify_migration.sql` to verify migration
3. Create individual key: `python manage_api_keys.py create --name "My Key" --email "user@example.com" --tier "free"`
   - Creates hidden personal org automatically
4. Create org key: `python manage_api_keys.py create --name "Team Key" --email "admin@acme.com" --organization "Acme Corp"`
   - Creates visible real organization
5. Verify limits work: Each individual now has their own 2-key limit (not shared!)

## Troubleshooting

### Common Issues

**"Invalid API key" (401 Error)**
- Check key is typed correctly (copy-paste to avoid typos)
- Verify key hasn't expired: `python manage_api_keys.py list`
- Check key is active in database
- Ensure correct Authorization header format: `Authorization: Bearer <key>`

**"Rate limit exceeded" (429 Error)**
- Check current limits: `python manage_api_keys.py list`
- View usage patterns: `python manage_api_keys.py usage "Client Name" --days 1`
- Increase limits if legitimate: Create new key with higher limits
- Investigate if potential abuse

**Database Connection Issues**
- Verify Supabase credentials in `.env`
- Check Supabase project status in dashboard
- Verify service role key has correct permissions
- Check server logs: `tail -f legal_rag_server.log`

**Usage Data Not Appearing**
- Confirm `MCP_API_AUTH_DB_ENABLED=true` in `.env`
- Check database connection successful
- Verify requests are being made (not just health checks)
- Query database directly: `SELECT COUNT(*) FROM api_key_usage;`

**digest() Function Type Casting Errors (Phase 3C)**
- **Error**: `function digest(bytea, unknown) does not exist`
- **Cause**: PostgreSQL requires explicit type casts for `digest()` parameters in some configurations
- **Quick Fix**: Run `migrations/005b_fix_digest_type_casting.sql` in Supabase SQL Editor
- **Full Guide**: See `TROUBLESHOOTING_DIGEST_FUNCTION.md` for detailed diagnosis and testing
- **Test**: Run `migrations/PHASE2_test_digest_function.sql` to verify digest() works
- **Verify**: Run `migrations/PHASE6_verify_fix.sql` after applying the fix
- **Prevention**: Migration files already include proper type casts (`::bytea` and `'sha256'::text`)

## Support

For detailed documentation, see:
- `implementation-plan.md` - Complete implementation guide
- `docs/API_KEY_MANAGEMENT.md` - Comprehensive API key management guide
- `requirements.md` - Feature requirements and architecture

---

> **Note:** These tasks are also listed in context within `implementation-plan.md`. This file provides a focused checklist of manual steps required for deployment and testing.
