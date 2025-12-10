# Phase 3A: Email-Based User Management - Deployment Steps

## Status: ✅ Code Complete - Ready for Database Migration

### What Was Implemented

✅ **Database Migration Created**: `migrations/002_add_email_to_api_keys.sql`
✅ **Python Script Updated**: `manage_api_keys.py` now supports `--email` and `--organization`
✅ **Documentation Updated**: 
   - `implementation-plan.md` - Added Phase 3A section
   - `action-required.md` - Added Phase 3A checklist

### Next Steps (YOU MUST DO THIS)

## Step 1: Run Database Migration in Supabase

1. **Open Supabase Dashboard**
   - Go to https://supabase.com
   - Select your Legal RAG project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar

3. **Run Migration**
   - Open the file: `migrations/002_add_email_to_api_keys.sql`
   - Copy ALL contents (245 lines)
   - Paste into Supabase SQL Editor
   - Click **"Run"** or press `Ctrl+Enter`

4. **Verify Success**
   - Should see: "Success. No rows returned"
   - Run verification query:
   ```sql
   SELECT column_name, data_type, is_nullable 
   FROM information_schema.columns 
   WHERE table_name = 'api_keys' 
   AND column_name IN ('email', 'organization');
   ```
   - Should return 2 rows (email and organization columns)

## Step 2: Update Existing Keys (Optional)

If you want to add email to your existing keys:

```sql
-- Update existing keys with default email
UPDATE api_keys 
SET email = 'admin@thejolawfirm.com', 
    organization = 'The Jo Law Firm'
WHERE email IS NULL;
```

## Step 3: Test Phase 3A

```bash
# Create a new key with email and organization
python manage_api_keys.py create \
    --name "Production Server" \
    --email "prod@thejolawfirm.com" \
    --organization "The Jo Law Firm"

# List all keys (should show new columns)
python manage_api_keys.py list

# Create another key for same email (testing multiple keys per user)
python manage_api_keys.py create \
    --name "Staging Server" \
    --email "prod@thejolawfirm.com" \
    --organization "The Jo Law Firm"

# List again to see both keys
python manage_api_keys.py list
```

## Step 4: Test Database Functions

```sql
-- Get all keys for a specific user
SELECT * FROM get_keys_by_email('prod@thejolawfirm.com');

-- Get organization statistics
SELECT * FROM get_organization_stats('The Jo Law Firm');
```

## Features Added

### 1. Email as Unique Identifier
- Each user identified by email address
- Email must be unique per user
- Prevents duplicate user accounts

### 2. Organization Tracking
- Track which company/firm owns keys
- Query all keys for an organization
- Generate organization-level stats

### 3. Multiple Keys Per User
- Same email can have multiple keys
- Example: "Production", "Staging", "Dev" keys
- Max 10 keys per email (enforced by trigger)

### 4. Email Format Validation
- Basic regex validation on email format
- Prevents obviously invalid emails

### 5. Helper Functions
- `get_keys_by_email(email)` - Get all keys for a user
- `get_organization_stats(org)` - Get org statistics

## Updated Command Format

### Old Way (Still Works)
```bash
python manage_api_keys.py create --name "Client Name"
```

### New Way (Recommended)
```bash
python manage_api_keys.py create \
    --name "Production Server" \
    --email "user@example.com" \
    --organization "Company Name"
```

## Benefits

✅ **Duplicate Prevention** - Email uniqueness prevents duplicate users
✅ **Better Organization** - Track ownership by firm/team
✅ **Flexible Key Management** - Multiple keys per user for different environments
✅ **User-Friendly** - Keep friendly names like "Production", use email as ID
✅ **Backward Compatible** - Existing keys without email still work

## Troubleshooting

### Error: "Could not find the 'email' column"
**Solution**: Run the migration in Supabase first!

### Error: "Maximum 10 active API keys per email address"
**Solution**: User already has 10 keys. Revoke old ones or increase limit in migration.

### Error: "email format_check constraint violated"
**Solution**: Email is not valid format. Use proper email like `user@example.com`

## Rollback (If Needed)

If you need to rollback Phase 3A:

```sql
-- WARNING: This deletes email and organization data!
DROP TRIGGER IF EXISTS trigger_check_api_key_limit ON api_keys;
DROP FUNCTION IF EXISTS check_api_key_limit();
DROP FUNCTION IF EXISTS get_keys_by_email(TEXT);
DROP FUNCTION IF EXISTS get_organization_stats(TEXT);
ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS email_format_check;
DROP INDEX IF EXISTS idx_api_keys_email_unique;
DROP INDEX IF EXISTS idx_api_keys_email;
DROP INDEX IF EXISTS idx_api_keys_organization;
ALTER TABLE api_keys DROP COLUMN IF EXISTS email;
ALTER TABLE api_keys DROP COLUMN IF EXISTS organization;
```

---

## Summary

**Phase 3A is code-complete!** 

All you need to do is:
1. ✅ Run `migrations/002_add_email_to_api_keys.sql` in Supabase SQL Editor
2. ✅ Test with `python manage_api_keys.py create --name "Test" --email "test@example.com"`
3. ✅ Verify with `python manage_api_keys.py list`

Then you're ready to use email-based user management! 🎉

