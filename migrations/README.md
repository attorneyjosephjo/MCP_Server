# Database Migrations

## Working SQL Files

### `WORKING_COMPLETE_STRUCTURE.sql` ✅
**Status:** Production-ready, tested and working

This is the **single source of truth** for your database structure. It includes:

- ✅ All tables (api_key_tiers, organizations, api_keys, api_key_usage)
- ✅ All functions (using MD5 - no extensions required)
- ✅ All triggers and views
- ✅ Row Level Security policies
- ✅ 5 subscription tiers (free → enterprise)
- ✅ Individual and organizational API key support

**When to use:**
- Setting up a fresh database
- Resetting your database structure
- Reference for the current schema

**How to use:**
1. Open Supabase SQL Editor
2. Copy the entire contents of this file
3. Run it
4. Done!

## Archive Folder

The `archive/` folder contains old migration files that were used during development. These are kept for historical reference only.

**Do not use these files** - they may have issues or require extensions that aren't available.

### Archived Files:
- `001_create_api_keys_tables.sql` - Initial tables
- `002_add_email_to_api_keys.sql` - Email column addition
- `003_add_tier_based_limits.sql` - Tier-based limits
- `004_organizations_and_limits.sql` - Organizations table
- `005_split_individuals_into_separate_orgs.sql` - Individual orgs (with digest)
- `000_COMPLETE_STRUCTURE.sql` - Complete structure (with pgcrypto)
- `000b_USE_MD5_ALTERNATIVE.sql` - MD5 fix only
- Various fix files (002b, 004b, 005b)

## Database Schema Overview

```
api_key_tiers
├── tier_name (PK)
├── max_keys_per_organization
├── rate_limit_per_minute
├── rate_limit_per_hour
└── rate_limit_per_day

organizations
├── id (PK)
├── name
├── slug (unique)
├── is_individual (boolean)
├── tier → api_key_tiers
└── primary_contact_email

api_keys
├── id (PK)
├── key_hash (unique, SHA-256)
├── key_prefix (display)
├── client_name
├── email
├── organization_id → organizations
└── tier (legacy)

api_key_usage
├── id (PK)
├── api_key_id → api_keys
├── timestamp
├── endpoint
├── method
└── status_code
```

## Key Features

### Organization Types

1. **Real Organizations** (`is_individual = false`)
   - Created manually: `python manage_api_keys.py create-org`
   - Visible in UI
   - Example: "Acme Startup LLC", "Law Firm"

2. **Individual Organizations** (`is_individual = true`)
   - Auto-created when user creates key without org
   - Hidden from UI
   - Slug: `user-{md5 hash}`
   - Example: "Personal - john@example.com"

### Subscription Tiers

| Tier | Keys | Requests/min | Price |
|------|------|--------------|-------|
| Free | 2 | 10 | $0 |
| Basic | 5 | 30 | $29 |
| Professional | 10 | 60 | $99 |
| Enterprise | 50 | 120 | $499 |
| Custom | 999 | 999 | Custom |

### Security Features

- ✅ Row Level Security (RLS) enabled
- ✅ Service role policies
- ✅ SHA-256 key hashing (never store plaintext)
- ✅ Rate limiting per tier
- ✅ Organization-based key limits
- ✅ Usage tracking and analytics

## Testing

After running the migration, verify with:

```bash
python reset_database.py
```

Then create test keys:

```bash
# Individual key
python manage_api_keys.py create --name "My Key" --email "test@example.com" --tier free

# Organizational key
python manage_api_keys.py create-org --name "Test Org" --tier basic --email "admin@test.com"
python manage_api_keys.py create --name "Org Key" --organization "Test Org" --email "dev@test.com"

# List everything
python manage_api_keys.py list
python manage_api_keys.py orgs
```

## Troubleshooting

### Issue: `digest() function does not exist`
**Solution:** The working SQL file uses `md5()` instead, which is built-in. Make sure you're using `WORKING_COMPLETE_STRUCTURE.sql`.

### Issue: `Table already exists`
**Solution:** The migration drops existing tables first. Safe to re-run.

### Issue: `Permission denied for extension`
**Solution:** The working version doesn't require any extensions except `uuid-ossp` (which is enabled by default in Supabase).

## Version History

- **v3.0** (2025-12-10) - Working version with MD5 (no extensions)
- **v2.0** (2025-12-10) - Complete structure with pgcrypto
- **v1.0** (2025-12-10) - Initial incremental migrations

---

**Current Version:** v3.0 (Working)
**Last Updated:** 2025-12-10
**Status:** ✅ Production Ready
