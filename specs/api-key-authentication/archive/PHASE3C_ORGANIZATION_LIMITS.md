# Phase 3C: Organization-Based API Key Limits

## Problem Statement

**Phase 3B had critical design flaws:**

1. ❌ **Limits were per email** - A company with 50 employees could each create 10 keys = 500 keys total!
2. ❌ **No unique organization ID** - Two "Smith Law Firm" companies would conflict
3. ❌ **No individual user support** - Solo practitioners had no proper category

## Solution: Organization-Based Architecture

Phase 3C introduces proper organization management with:
- ✅ **Limits per organization** (not per user)
- ✅ **Unique organization IDs** (UUID + slug)
- ✅ **Individual user support** (special "individuals" organization)

## Architecture

```
┌──────────────────────────────────────────────┐
│ ORGANIZATIONS TABLE                          │
│                                              │
│ ┌─────────────────────────────────────────┐ │
│ │ id: UUID (unique)                        │ │
│ │ name: "Acme Corp"                        │ │
│ │ slug: "acme-corp" (unique, URL-safe)    │ │
│ │ tier: "professional"                     │ │
│ │ keys_limit: 10 (from tier)              │ │
│ └─────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   │
                   │ Foreign Key
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ API_KEYS TABLE                               │
│                                              │
│ ┌─────────────────────────────────────────┐ │
│ │ id: UUID                                 │ │
│ │ organization_id: UUID → organizations.id │ │
│ │ email: "user@acme.com"                   │ │
│ │ client_name: "Production Server"         │ │
│ └─────────────────────────────────────────┘ │
│                                              │
│ All keys count against ORGANIZATION limit   │
│ (not individual user limit)                 │
└──────────────────────────────────────────────┘
```

## Key Changes

### 1. Organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,                   -- Display name (can duplicate)
    slug TEXT UNIQUE NOT NULL,            -- Unique identifier (e.g., "acme-corp")
    tier TEXT DEFAULT 'free',
    primary_contact_email TEXT,
    billing_email TEXT,
    website TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Special "Individuals" Organization

For solo practitioners without a company:

```sql
INSERT INTO organizations (id, name, slug, tier)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Individual Users',
    'individuals',
    'free'
);
```

### 3. API Keys Link to Organizations

```sql
ALTER TABLE api_keys 
ADD COLUMN organization_id UUID REFERENCES organizations(id);
```

## Setup

### Step 1: Run Migration

Execute `migrations/004_organizations_and_limits.sql` in Supabase SQL Editor.

This will:
- Create `organizations` table
- Add `organization_id` to `api_keys`
- Migrate existing data (creates orgs from existing organization names)
- Update triggers to check org-level limits
- Create helper functions

### Step 2: Verify Migration

```sql
-- Check organizations were created
SELECT * FROM organizations;

-- Check keys are linked
SELECT 
    k.client_name,
    o.name as org_name,
    o.slug,
    o.tier
FROM api_keys k
LEFT JOIN organizations o ON k.organization_id = o.id;
```

## Usage

### Create Organization

```bash
# Create a company organization
python manage_api_keys.py create-org \
    --name "Acme Corporation" \
    --tier professional \
    --email "admin@acme.com" \
    --website "https://acme.com"

# Slug is auto-generated: "acme-corporation"
```

### List Organizations

```bash
python manage_api_keys.py orgs
```

Output:
```
┌────────────────── Organizations ──────────────────┐
│ Name            │ Slug          │ Tier │ Keys  │  │
├─────────────────┼───────────────┼──────┼───────┤  │
│ Acme Corp       │ acme-corp     │ PRO  │ 8/10  │  │
│ Smith Law Firm  │ smith-law-... │ BASIC│ 3/5   │  │
│ Big Corp        │ big-corp      │ ENT  │ 25/50 │  │
└─────────────────┴───────────────┴──────┴───────┘  │
```

### Create API Key for Organization

```bash
# Organization gets created automatically if it doesn't exist
python manage_api_keys.py create \
    --name "Production API" \
    --email "dev@acme.com" \
    --organization "Acme Corporation" \
    --tier professional

# Keys count against ORGANIZATION limit (not user limit)
```

### Create API Key for Individual

```bash
# For solo practitioners (no company)
python manage_api_keys.py create \
    --name "Personal API" \
    --email "solo@lawyer.com" \
    --organization "Individual"

# Or omit --organization entirely (defaults to Individual)
python manage_api_keys.py create \
    --name "Personal API" \
    --email "solo@lawyer.com"
```

### Change Organization Tier

```bash
# Upgrade organization
python manage_api_keys.py change-tier acme-corporation enterprise

# Note: Uses SLUG, not name
```

### List Keys (Now Shows Organization)

```bash
python manage_api_keys.py list
```

Output now includes organization column:
```
┌──────────────────────── API Keys ────────────────────────┐
│ Name    │ Email          │ Organization  │ Tier │ Status │
├─────────┼────────────────┼───────────────┼──────┼────────┤
│ Prod    │ dev@acme.com   │ Acme Corp     │ PRO  │ Active │
│ Staging │ dev2@acme.com  │ Acme Corp     │ PRO  │ Active │
│ Dev     │ dev@acme.com   │ Acme Corp     │ PRO  │ Active │
└─────────┴────────────────┴───────────────┴──────┴────────┘

3 keys from same org count against org limit (not per user)
```

## Example Scenarios

### Scenario 1: Law Firm with Multiple Employees

```bash
# Create organization (professional tier = 10 keys max)
python manage_api_keys.py create-org \
    --name "Smith & Associates Law Firm" \
    --tier professional \
    --email "admin@smithlaw.com"

# Slug: "smith-associates-law-firm"

# Employee 1 creates keys
python manage_api_keys.py create \
    --name "Partner Laptop" \
    --email "partner1@smithlaw.com" \
    --organization "Smith & Associates Law Firm"

# Employee 2 creates keys
python manage_api_keys.py create \
    --name "Associate Laptop" \
    --email "associate1@smithlaw.com" \
    --organization "Smith & Associates Law Firm"

# ... 8 more employees create keys ...

# Employee 11 tries to create a key
python manage_api_keys.py create \
    --name "Paralegal Laptop" \
    --email "paralegal@smithlaw.com" \
    --organization "Smith & Associates Law Firm"

# ERROR: Organization "Smith & Associates Law Firm" has reached 
#        maximum of 10 API keys for professional tier
```

### Scenario 2: Two Companies with Same Name

```bash
# Company 1 in California
python manage_api_keys.py create-org \
    --name "Smith Law Firm" \
    --email "info@smithlaw-ca.com"
# Slug: "smith-law-firm"

# Company 2 in New York
python manage_api_keys.py create-org \
    --name "Smith Law Firm" \
    --email "info@smithlaw-ny.com"
# ERROR: Slug "smith-law-firm" already exists

# Solution: Add location to name
python manage_api_keys.py create-org \
    --name "Smith Law Firm New York" \
    --email "info@smithlaw-ny.com"
# Slug: "smith-law-firm-new-york" ✅
```

### Scenario 3: Solo Practitioner (Individual)

```bash
# Solo lawyer (no company)
python manage_api_keys.py create \
    --name "Office Desktop" \
    --email "john@solo-lawyer.com" \
    --organization "Individual"

# Gets assigned to special "individuals" organization
# Free tier = 2 keys max (shared across all individuals)
```

## Database Queries

### Get All Keys for an Organization

```sql
-- By organization ID
SELECT * FROM get_keys_by_organization('org-uuid-here');

-- By organization name (join required)
SELECT k.* 
FROM api_keys k
JOIN organizations o ON k.organization_id = o.id
WHERE o.slug = 'acme-corp';
```

### Get Organization Usage Summary

```sql
SELECT * FROM get_organization_usage('org-uuid-here');
```

Returns:
- Organization name
- Current tier
- Keys used / limit
- Total requests
- Number of unique users (emails)

### Find Organizations Near Limit

```sql
SELECT 
    o.name,
    o.tier,
    COUNT(k.id) as keys_used,
    t.max_keys_per_email as keys_limit
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id AND k.is_active = true
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
GROUP BY o.name, o.tier, t.max_keys_per_email
HAVING COUNT(k.id) >= t.max_keys_per_email * 0.8  -- 80% of limit
ORDER BY (COUNT(k.id)::float / t.max_keys_per_email) DESC;
```

### List Organizations by Revenue Potential

```sql
SELECT 
    o.name,
    o.tier,
    t.price_monthly,
    COUNT(k.id) as total_keys,
    COUNT(DISTINCT k.email) as unique_users
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
LEFT JOIN api_key_tiers t ON t.tier_name = o.tier
WHERE o.slug != 'individuals'
GROUP BY o.name, o.tier, t.price_monthly
ORDER BY t.price_monthly DESC, total_keys DESC;
```

## Migration from Phase 3B

The migration automatically handles existing data:

1. **Creates organizations** from unique `organization` names in `api_keys`
2. **Generates slugs** from organization names
3. **Links keys** to new organizations via `organization_id`
4. **Assigns individuals** keys without organization to special "individuals" org

No manual data migration required!

## Benefits

✅ **Correct Limits** - 1 organization = 1 tier limit (not per user)
✅ **Unique IDs** - No name collisions (UUID + slug)
✅ **Individual Support** - Solo practitioners handled properly
✅ **Scalable** - Can support thousands of organizations
✅ **Clear Ownership** - Each key belongs to exactly one organization
✅ **Flexible** - Easy to add billing, contacts, metadata per org

## Comparison: Phase 3B vs 3C

| Aspect | Phase 3B (Bad) | Phase 3C (Good) |
|--------|----------------|-----------------|
| **Limit Scope** | Per email | Per organization |
| **100-person company** | 100 × 10 = 1000 keys | 1 × 10 = 10 keys |
| **Organization ID** | Name (string) | UUID + slug |
| **Name collisions** | Possible | Impossible |
| **Individuals** | No proper support | Special org |
| **Billing** | Per user? | Per organization |

## Common Tasks

### Upgrade All Keys for an Organization

```sql
-- Change tier (updates all keys automatically)
SELECT change_organization_tier(
    (SELECT id FROM organizations WHERE slug = 'acme-corp'),
    'enterprise'
);
```

### Find Which Organization Uses Most Keys

```sql
SELECT 
    o.name,
    COUNT(k.id) as total_keys
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
WHERE k.is_active = true
GROUP BY o.name
ORDER BY total_keys DESC
LIMIT 10;
```

### Revoke All Keys for an Organization

```sql
UPDATE api_keys
SET is_active = false
WHERE organization_id = (
    SELECT id FROM organizations WHERE slug = 'bad-org'
);
```

## Troubleshooting

### Error: "Organization not found"

**Problem**: Trying to create a key with a non-existent organization

**Solution**: The organization is created automatically now! Just use the organization name.

### Error: "Organization has reached maximum"

**Problem**: Organization hit their tier limit

**Solution**: 
1. Revoke unused keys, OR
2. Upgrade organization tier

```bash
python manage_api_keys.py change-tier acme-corp professional
```

### Duplicate Organization Names

**Problem**: Two orgs with same name need different slugs

**Solution**: Add differentiator to name:
- "Smith Law Firm" → "Smith Law Firm California"
- "Smith Law Firm" → "Smith Law Firm Texas"

Slugs will be unique: `smith-law-firm-california`, `smith-law-firm-texas`

### Error: "function digest(bytea, unknown) does not exist"

**Problem**: PostgreSQL type casting error when running migration 005 or creating individual organizations

**Root Cause**: Some PostgreSQL configurations require explicit type casts for both parameters of the `digest()` function from the pgcrypto extension.

**Solution**: The migration files already include proper type casts. If you encounter this error:

1. **Quick Fix**: Run the standalone fix script in Supabase SQL Editor:
   ```sql
   -- migrations/005b_fix_digest_type_casting.sql
   ```

2. **Verify pgcrypto extension**:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'pgcrypto';
   ```

3. **Test digest() function** (should succeed):
   ```sql
   SELECT encode(digest('test@example.com'::bytea, 'sha256'::text), 'hex');
   ```

4. **Test the fixed function**:
   ```sql
   SELECT get_or_create_individual_org('test@example.com', 'free');
   ```

**Full Troubleshooting Guide**: See `TROUBLESHOOTING_DIGEST_FUNCTION.md` for comprehensive diagnosis and testing steps.

**Technical Details**:
- The `digest()` function signature is: `digest(data bytea, type text)`
- Some PostgreSQL versions don't automatically cast string literals to `bytea` and `text`
- Solution: Use explicit casts: `digest(email::bytea, 'sha256'::text)`
- Affected lines: Migration 005 line 50 (DO block) and line 205 (function definition)
- Status: **Fixed** - All migration files now include proper type casts

---

**Phase 3C Complete!** Limits are now properly enforced at the organization level, with unique IDs and proper individual user support. 🎉

