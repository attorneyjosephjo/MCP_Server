# Quick Reference Guide

## 🗂️ Clean Migrations Structure

```
migrations/
├── WORKING_COMPLETE_STRUCTURE.sql  ✅ Use this!
├── README.md                       📖 Documentation
└── archive/                        🗄️ Old files (reference only)
    ├── 001_create_api_keys_tables.sql
    ├── 002_add_email_to_api_keys.sql
    ├── 003_add_tier_based_limits.sql
    ├── 004_organizations_and_limits.sql
    ├── 005_split_individuals_into_separate_orgs.sql
    └── ... (other old files)
```

## 🚀 Quick Start

### 1. Setup Database

```bash
# Open Supabase SQL Editor
# Copy and run: migrations/WORKING_COMPLETE_STRUCTURE.sql
# Verify:
python reset_database.py
```

### 2. Create Organizations

```bash
# Real organization
python manage_api_keys.py create-org \
  --name "Acme Corp" \
  --tier professional \
  --email "admin@acme.com"

# List organizations
python manage_api_keys.py orgs
```

### 3. Create API Keys

```bash
# Individual key (auto-creates hidden org)
python manage_api_keys.py create \
  --name "My Personal Key" \
  --email "john@example.com" \
  --tier free

# Organizational key
python manage_api_keys.py create \
  --name "Production API" \
  --organization "Acme Corp" \
  --email "dev@acme.com"

# List all keys
python manage_api_keys.py list
```

## 📊 Database Structure

### Tables
- `api_key_tiers` - 5 subscription tiers
- `organizations` - Real orgs + individual orgs
- `api_keys` - API keys linked to organizations
- `api_key_usage` - Request tracking

### Key Concepts

**Individual Organizations** (Hidden)
```
User creates key → Auto-create personal org → Link key to org
john@example.com → "Personal - john@example.com" → user-a1b2c3d4
```

**Real Organizations** (Visible)
```
Admin creates org → Users create keys in org → Share org limits
"Acme Corp" → API keys for multiple users → 10 keys max (professional tier)
```

### Subscription Tiers

| Tier         | Keys | Requests/min | Monthly |
|--------------|------|--------------|---------|
| Free         | 2    | 10           | $0      |
| Basic        | 5    | 30           | $29     |
| Professional | 10   | 60           | $99     |
| Enterprise   | 50   | 120          | $499    |
| Custom       | 999  | 999          | Custom  |

## 🔧 Management Commands

```bash
# Organizations
python manage_api_keys.py create-org --name "Name" --tier TIER --email EMAIL
python manage_api_keys.py orgs
python manage_api_keys.py change-tier --organization "Name" --tier TIER

# API Keys
python manage_api_keys.py create --name "Name" --email EMAIL [--organization ORG] [--tier TIER]
python manage_api_keys.py list
python manage_api_keys.py revoke --key-id UUID
python manage_api_keys.py rotate --key-id UUID
python manage_api_keys.py usage --key-id UUID

# Maintenance
python manage_api_keys.py cleanup  # Remove expired keys
python manage_api_keys.py tiers    # Show tier limits
```

## 🔍 Useful SQL Queries

```sql
-- Show all organizations (including hidden individual orgs)
SELECT * FROM organizations ORDER BY is_individual, created_at;

-- Show organization with usage
SELECT * FROM list_organizations_with_usage(true);

-- Show keys by organization
SELECT * FROM get_keys_by_organization('org-uuid-here');

-- Show individual users
SELECT * FROM individual_users_summary;

-- Show real organizations
SELECT * FROM organization_summary;

-- Tier usage summary
SELECT * FROM tier_usage_summary;
```

## 🐛 Troubleshooting

### Problem: `digest() function does not exist`
**Solution:** Use `WORKING_COMPLETE_STRUCTURE.sql` (uses MD5, no extensions needed)

### Problem: Individual keys don't work
**Solution:** Run `migrations/000b_USE_MD5_ALTERNATIVE.sql` to update the function

### Problem: Unicode error in terminal
**Solution:** Windows Korean locale issue. Use SQL Editor for queries or change terminal encoding

### Problem: Organization not found
**Solution:** Create org first with `create-org` or use `--email` to create individual key

## 📁 File Reference

### Working Files
- `migrations/WORKING_COMPLETE_STRUCTURE.sql` - Main database structure
- `migrations/README.md` - Detailed migration documentation
- `manage_api_keys.py` - CLI tool for key management
- `reset_database.py` - Verification script
- `DATABASE_RESET_GUIDE.md` - Step-by-step reset guide

### Archive (Historical Reference)
- `migrations/archive/*` - Old migration files (don't use)

### Troubleshooting Files
- `TROUBLESHOOTING_DIGEST_FUNCTION.md` - Digest function issues
- `show_all_orgs.sql` - Query to view all orgs
- `fix_pgcrypto.sql` - Extension troubleshooting

## ✅ What's Working Now

✅ Database structure is clean and correct
✅ Can create real organizations
✅ Can create individual API keys (auto-org creation)
✅ Can create organizational API keys
✅ Tier-based limits enforced
✅ Rate limiting configured
✅ Usage tracking enabled
✅ No extensions required (uses built-in MD5)

## 🎯 Next Steps

1. ✅ Database structure complete
2. 📝 Integrate API key authentication into MCP server
3. 🔐 Implement middleware for key validation
4. 📊 Add usage tracking to endpoints
5. 🎨 Build admin dashboard (optional)

---

**Version:** 3.0
**Status:** ✅ Production Ready
**Last Updated:** 2025-12-10
