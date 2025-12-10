# Database Reset Guide

This guide will help you reset your database structure to fix the `digest()` function error.

## Problem

The error you're encountering:
```
function digest(bytea, text) does not exist
```

This happens because the `pgcrypto` extension is not enabled in your database.

## Solution: Apply Complete Structure Migration

### Step 1: Open Supabase SQL Editor

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Click on **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Run the Complete Structure Migration

1. Open the file: `migrations/000_COMPLETE_STRUCTURE.sql`
2. Copy **ALL** the contents
3. Paste into the SQL Editor
4. Click **Run** (or press Ctrl+Enter)

**What this migration does:**
- ✅ Enables `pgcrypto` extension (fixes the digest error)
- ✅ Drops all existing tables cleanly (no conflicts)
- ✅ Creates proper table structure:
  - `api_key_tiers` (5 tiers: free, basic, professional, enterprise, custom)
  - `organizations` (supports both companies and individuals)
  - `api_keys` (with organization-based limits)
  - `api_key_usage` (tracking and analytics)
- ✅ Creates all necessary functions:
  - `get_or_create_individual_org()` - Creates personal orgs for individuals
  - `check_api_key_limit_by_organization()` - Enforces limits
  - Organization management functions
  - Rate limiting functions
  - Usage analytics functions
- ✅ Creates reporting views
- ✅ Sets up Row Level Security

### Step 3: Verify the Setup

Run the verification script:

```bash
python reset_database.py
```

When prompted, type `YES` and press Enter. The script will verify that all tables and functions were created correctly.

### Step 4: Test Creating Organizations and Keys

Now you should be able to create organizations and API keys without errors:

```bash
# Create organizations (these already work)
python manage_api_keys.py create-org --name "Test Company" --tier free --email "admin@test.com"

# Create individual API key (this should now work!)
python manage_api_keys.py create --name "My Personal Key" --email "john@example.com" --tier free

# Create organizational API key
python manage_api_keys.py create --name "Company Key" --organization "Test Company" --tier free --email "dev@test.com"

# List organizations
python manage_api_keys.py orgs

# List all API keys
python manage_api_keys.py list
```

## What Changed?

### Before (Broken)
- ❌ `pgcrypto` extension not enabled
- ❌ `digest()` function unavailable
- ❌ Creating individual API keys failed
- ❌ Type mismatches in functions

### After (Fixed)
- ✅ `pgcrypto` extension enabled
- ✅ `digest()` function works correctly
- ✅ Individual API keys can be created
- ✅ All type casts are explicit
- ✅ Clean table structure with no conflicts

## Database Structure

### Tiers
```
free         - 2 keys, 10 req/min
basic        - 5 keys, 30 req/min
professional - 10 keys, 60 req/min
enterprise   - 50 keys, 120 req/min
custom       - 999 keys, unlimited
```

### Organizations
- **Real Organizations**: Companies with unique names and slugs
- **Individual Organizations**: Auto-created personal orgs (hidden from UI)
  - Slug format: `user-{hash of email}`
  - Example: `user-a3f5d8e2c1b9`

### API Keys
- Each key belongs to an organization
- Limits enforced at organization level
- Individual users get their own hidden organization
- Company users share organization limits

## Troubleshooting

### If the migration fails:

1. **Permission error**: Make sure you're using the `service_role` key in your `.env` file
2. **Function already exists**: The migration drops all existing functions first, so this shouldn't happen
3. **Extension error**: Your database might not support pgcrypto. Contact Supabase support.

### If verification fails:

Run these SQL queries manually in SQL Editor:

```sql
-- Check if pgcrypto is enabled
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

-- Should return one row. If not, run:
CREATE EXTENSION pgcrypto;

-- Test digest function
SELECT encode(digest('test'::bytea, 'sha256'::text), 'hex');

-- Should return a hash string
```

## Next Steps

After completing this reset:

1. ✅ Your database structure is now correct
2. ✅ You can create organizations and API keys
3. ✅ Rate limiting and usage tracking are enabled
4. 📝 Update your application code to use the new structure
5. 🔒 Implement API key authentication in your MCP server

See `DEPLOYMENT_GUIDE.md` for details on integrating API key authentication.
