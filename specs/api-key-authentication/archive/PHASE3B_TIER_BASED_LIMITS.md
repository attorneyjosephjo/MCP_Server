# Phase 3B: Tier-Based API Key Limits

## Overview

Phase 3B adds subscription-based limits where different companies/organizations can have different API key allowances based on their tier.

## Tier Structure

| Tier | Max Keys | Rate/Min | Rate/Hour | Rate/Day | Price/Month |
|------|----------|----------|-----------|----------|-------------|
| **Free** | 2 | 10 | 100 | 1,000 | $0 |
| **Basic** | 5 | 30 | 500 | 5,000 | $29 |
| **Professional** | 10 | 60 | 1,000 | 10,000 | $99 |
| **Enterprise** | 50 | 120 | 5,000 | 50,000 | $499 |
| **Custom** | 999 | 999 | 99,999 | 999,999 | Negotiated |

## Setup

### 1. Run Migration

Execute `migrations/003_add_tier_based_limits.sql` in Supabase SQL Editor.

This creates:
- `tier` column on `api_keys` table
- `api_key_tiers` configuration table
- Updated trigger for tier-based limits
- Helper functions for tier management

### 2. Verify Setup

```sql
-- Check tier configurations
SELECT * FROM api_key_tiers ORDER BY max_keys_per_email;

-- Check tier usage summary
SELECT * FROM tier_usage_summary;
```

## Usage

### Create Key with Tier

```bash
# Free tier (default)
python manage_api_keys.py create \
    --name "Production" \
    --email "user@example.com" \
    --organization "Company Name"

# Professional tier
python manage_api_keys.py create \
    --name "Production" \
    --email "user@example.com" \
    --organization "Company Name" \
    --tier professional

# Enterprise tier
python manage_api_keys.py create \
    --name "Production" \
    --email "cto@bigcorp.com" \
    --organization "Big Corp" \
    --tier enterprise
```

### List All Tiers

```bash
python manage_api_keys.py tiers
```

Output:
```
┌────────────── Subscription Tiers ──────────────┐
│ Tier          │ Max │ Rate │ Rate  │ Rate   │ │
│               │ Keys│ /Min │ /Hour │ /Day   │ │
├───────────────┼─────┼──────┼───────┼────────┤ │
│ FREE          │ 2   │ 10   │ 100   │ 1,000  │ │
│ BASIC         │ 5   │ 30   │ 500   │ 5,000  │ │
│ PROFESSIONAL  │ 10  │ 60   │ 1,000 │ 10,000 │ │
│ ENTERPRISE    │ 50  │ 120  │ 5,000 │ 50,000 │ │
└───────────────┴─────┴──────┴───────┴────────┘ │
```

### Change User Tier

```bash
# Upgrade user to professional
python manage_api_keys.py change-tier user@example.com professional

# Downgrade to basic (must have ≤5 keys)
python manage_api_keys.py change-tier user@example.com basic
```

### List Keys (Shows Tier)

```bash
python manage_api_keys.py list
```

Output now includes **Tier** column:
```
┌─────────────────────────────── API Keys ───────────────────────────────┐
│ ID  │ Name    │ Email           │ Organization │ Tier    │ Status     │
├─────┼─────────┼─────────────────┼──────────────┼─────────┼────────────┤
│ a1b │ Prod    │ user@example.com│ Company      │ free    │ 🟢 Active  │
│ c2d │ Staging │ user@example.com│ Company      │ free    │ 🟢 Active  │
└─────┴─────────┴─────────────────┴──────────────┴─────────┴────────────┘
```

## Features

### 1. Automatic Limit Enforcement

When creating a key, the system automatically checks the tier limit:

```bash
# Free tier user tries to create 3rd key
$ python manage_api_keys.py create --name "Dev" --email "user@example.com"
Error: Maximum 2 API keys allowed for free tier
```

### 2. Safe Downgrades

You cannot downgrade a tier if the user has more keys than the new tier allows:

```bash
# User has 8 keys, tries to downgrade to basic (max 5)
$ python manage_api_keys.py change-tier user@example.com basic
Cannot downgrade: User has 8 active keys but basic tier only allows 5
```

### 3. Query by Tier

```sql
-- Get all keys for a specific tier
SELECT * FROM api_keys WHERE tier = 'professional';

-- Get usage summary by tier
SELECT * FROM tier_usage_summary;

-- Get all users on enterprise tier
SELECT DISTINCT email, organization 
FROM api_keys 
WHERE tier = 'enterprise' AND is_active = true;
```

### 4. Organization-Wide Tier Management

Update all keys for an organization:

```sql
-- Upgrade entire organization to enterprise
UPDATE api_keys 
SET tier = 'enterprise' 
WHERE organization = 'The Jo Law Firm';
```

## Database Functions

### `get_tier_info(tier_name)`

Get configuration for a specific tier:

```sql
SELECT * FROM get_tier_info('professional');
```

### `change_user_tier(email, new_tier)`

Change a user's tier (with validation):

```sql
SELECT change_user_tier('user@example.com', 'professional');
```

### `tier_usage_summary` (View)

Summary statistics across all tiers:

```sql
SELECT * FROM tier_usage_summary;
```

Returns:
- Total users per tier
- Total/active keys per tier
- Total requests per tier
- Active percentage

## Migration from Phase 3A

If you already have keys from Phase 3A without tiers:

```sql
-- Option 1: Set all existing keys to free
UPDATE api_keys SET tier = 'free' WHERE tier IS NULL;

-- Option 2: Set by organization
UPDATE api_keys SET tier = 'professional' 
WHERE organization = 'The Jo Law Firm';

UPDATE api_keys SET tier = 'basic' 
WHERE organization = 'Moohan, Inc.';

-- Option 3: Set by email (if you know who paid)
UPDATE api_keys SET tier = 'enterprise' 
WHERE email = 'cto@bigcorp.com';
```

## Use Cases

### Use Case 1: Law Firm (Tiered Service)

```bash
# Basic tier - Small clients
python manage_api_keys.py create \
    --name "Small Client API" \
    --email "smallclient@example.com" \
    --organization "Small Law Firm" \
    --tier basic

# Professional tier - Medium clients
python manage_api_keys.py create \
    --name "Production" \
    --email "mediumclient@example.com" \
    --organization "Medium Law Firm" \
    --tier professional

# Enterprise tier - Large clients
python manage_api_keys.py create \
    --name "Production" \
    --email "cto@biglawfirm.com" \
    --organization "Big Law Firm" \
    --tier enterprise
```

### Use Case 2: SaaS Product

```bash
# Free trial - 2 keys
python manage_api_keys.py create \
    --name "Trial" \
    --email "trial@startup.com" \
    --tier free

# After 30 days, upgrade to paid
python manage_api_keys.py change-tier trial@startup.com professional
```

### Use Case 3: Internal Teams

```bash
# Dev team - basic tier
python manage_api_keys.py create \
    --name "Dev Environment" \
    --email "devteam@thejolawfirm.com" \
    --tier basic

# Production team - enterprise tier
python manage_api_keys.py create \
    --name "Production" \
    --email "prodteam@thejolawfirm.com" \
    --tier enterprise
```

## Monitoring & Analytics

### Query: Top Tier by Usage

```sql
SELECT tier, 
       COUNT(*) as total_keys,
       SUM(total_requests) as total_requests
FROM api_keys
WHERE is_active = true
GROUP BY tier
ORDER BY total_requests DESC;
```

### Query: Users at Tier Limit

```sql
SELECT 
    email,
    tier,
    COUNT(*) as keys_used,
    t.max_keys_per_email as keys_limit
FROM api_keys k
JOIN api_key_tiers t ON k.tier = t.tier_name
WHERE k.is_active = true
GROUP BY email, tier, t.max_keys_per_email
HAVING COUNT(*) >= t.max_keys_per_email;
```

### Query: Revenue Potential

```sql
SELECT 
    tier,
    COUNT(DISTINCT email) as unique_users,
    price_monthly,
    COUNT(DISTINCT email) * price_monthly as monthly_revenue
FROM api_keys k
JOIN api_key_tiers t ON k.tier = t.tier_name
WHERE k.is_active = true AND price_monthly IS NOT NULL
GROUP BY tier, price_monthly
ORDER BY monthly_revenue DESC;
```

## Customizing Tier Limits

### Add New Tier

```sql
INSERT INTO api_key_tiers (
    tier_name, 
    max_keys_per_email, 
    rate_limit_per_minute, 
    rate_limit_per_hour, 
    rate_limit_per_day, 
    price_monthly, 
    description
) VALUES (
    'startup',
    15,
    80,
    2000,
    20000,
    149.00,
    'Startup tier - perfect for growing companies'
);
```

### Update Existing Tier

```sql
-- Increase professional tier limits
UPDATE api_key_tiers 
SET max_keys_per_email = 15,
    rate_limit_per_hour = 2000
WHERE tier_name = 'professional';
```

## Security Considerations

1. **Tier stored in database** - Easy to upgrade/downgrade
2. **Limits enforced by trigger** - Cannot bypass by direct INSERT
3. **Rate limits per tier** - Prevents abuse at each level
4. **Audit trail** - All tier changes logged in database

## Rollback

If you need to remove tier-based limits:

```sql
-- Run rollback section from migration file
-- WARNING: This deletes tier configuration!
-- See migrations/003_add_tier_based_limits.sql
```

## Next Steps

- **Billing Integration**: Connect tiers to Stripe/payment system
- **Usage Alerts**: Notify when users approach tier limits
- **Auto-Upgrade Prompts**: Suggest upgrades when hitting limits
- **Tier Analytics Dashboard**: Visual reporting of tier adoption

---

**Phase 3B Complete!** Tier-based limits are now active. Users can have different key allowances based on their subscription tier. 🎉

