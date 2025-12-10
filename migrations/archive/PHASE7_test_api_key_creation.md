# Phase 7: Test API Key Creation via Python CLI

After applying the database fix (Phase 5), test the API key creation workflow.

## Prerequisites

1. Database fix has been applied (run `005b_fix_digest_type_casting.sql` in Supabase)
2. `.env` file is configured with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
3. Python dependencies are installed (`pip install -r requirements.txt`)

## Test Commands

### 1. Create API Key for Individual User

```bash
python manage_api_keys.py create --name "Test Key" --email "user@example.com" --tier "free"
```

**Expected Output:**
- Success message with API key displayed
- Organization auto-created with slug like `user-b4c9a289323b21a0`
- Key is linked to the personal organization

### 2. List All API Keys

```bash
python manage_api_keys.py list
```

**Expected Output:**
- Table showing all API keys
- The test key should appear with correct email and organization

### 3. Create Second Key for Same User (Test Limits)

```bash
python manage_api_keys.py create --name "Test Key 2" --email "user@example.com" --tier "free"
```

**Expected Output:**
- Success (free tier allows 2 keys)
- Both keys linked to the SAME personal organization
- Organization ID should match first key

### 4. Attempt Third Key (Should Fail)

```bash
python manage_api_keys.py create --name "Test Key 3" --email "user@example.com" --tier "free"
```

**Expected Output:**
- Error: "Maximum number of API keys reached for this email (2/2)"
- This validates tier-based limits are working

### 5. Verify in Database

Run this query in Supabase SQL Editor:

```sql
SELECT
    k.id,
    k.client_name,
    k.email,
    k.key_prefix,
    o.slug as org_slug,
    o.is_individual,
    o.tier
FROM api_keys k
JOIN organizations o ON o.id = k.organization_id
WHERE k.email = 'user@example.com'
ORDER BY k.created_at;
```

**Expected Results:**
- All keys have the same `organization_id`
- `org_slug` starts with `user-`
- `is_individual` = `true`
- `tier` = `free`

### 6. Clean Up Test Data

```bash
python manage_api_keys.py revoke "user@example.com"
```

**Expected Output:**
- All keys for the email are revoked
- Keys remain in database but marked as inactive

### 7. Test Pro Tier (10 Keys Limit)

```bash
# Create API key with pro tier
python manage_api_keys.py create --name "Pro Key 1" --email "pro@example.com" --tier "pro"

# List to verify
python manage_api_keys.py list

# Clean up
python manage_api_keys.py revoke "pro@example.com"
```

## Success Criteria

✅ All tests pass when:
- Individual organizations are auto-created on first key creation
- Multiple keys for same email use the same organization
- Tier-based limits are enforced correctly
- Database queries show proper structure
- No `digest()` function errors occur

## Troubleshooting

If you encounter errors:

1. **"function digest(bytea, unknown) does not exist"**
   - The database fix wasn't applied
   - Run `migrations/005b_fix_digest_type_casting.sql` in Supabase

2. **"Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"**
   - Check `.env` file exists and has correct values
   - Ensure `.env` is in the project root directory

3. **"Maximum number of API keys reached"**
   - Expected behavior when tier limit is hit
   - Revoke old keys or upgrade tier

4. **"Error creating individual organization"**
   - Check Supabase connection
   - Verify the function exists: `SELECT * FROM pg_proc WHERE proname = 'get_or_create_individual_org';`
   - Check logs in Supabase Dashboard

## Next Steps

After successful testing:
1. Create production API keys for actual users
2. Document the API key creation process for end users
3. Set up monitoring for key usage
4. Configure rate limiting in the MCP server
