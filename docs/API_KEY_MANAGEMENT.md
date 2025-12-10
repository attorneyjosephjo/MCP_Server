# API Key Management Guide

Complete guide for managing API keys in the Legal RAG MCP Server.

## Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Creating API Keys](#creating-api-keys)
4. [Listing API Keys](#listing-api-keys)
5. [Revoking API Keys](#revoking-api-keys)
6. [Rotating API Keys](#rotating-api-keys)
7. [Monitoring Usage](#monitoring-usage)
8. [Rate Limiting](#rate-limiting)
9. [Troubleshooting](#troubleshooting)

## Overview

The Legal RAG MCP Server supports two authentication modes:

### Environment Variable Mode (Phase 1)
- **Best for**: 2-10 clients
- **Setup**: Simple environment variables
- **Features**: Basic authentication
- **No database required**

### Database Mode (Phase 2)
- **Best for**: Unlimited clients
- **Setup**: Supabase database migration
- **Features**: Rate limiting, usage tracking, expiration, analytics
- **Requires**: Supabase connection

## Setup

### Prerequisites

1. Supabase project with connection configured
2. Python environment with dependencies installed:
   ```bash
   pip install supabase-py python-dotenv rich
   ```

### Database Migration

Run the migration SQL in your Supabase SQL Editor:

1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `migrations/001_create_api_keys_tables.sql`
3. Execute the migration
4. Verify tables created:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('api_keys', 'api_key_usage');
   ```

### Enable Database Mode

Update your `.env` file:

```bash
# Enable database-backed authentication
MCP_API_AUTH_DB_ENABLED=true
```

## Creating API Keys

### Basic Creation

Create a simple API key:

```bash
python manage_api_keys.py create --name "Production Client"
```

**Output**:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ Success                                   ┃
┠──────────────────────────────────────────────┨
┃ API Key Created Successfully!                ┃
┃                                              ┃
┃ ⚠️  IMPORTANT: Save this key now - it       ┃
┃ cannot be retrieved later!                   ┃
┃                                              ┃
┃ API Key: abc123...xyz789                     ┃
┃ Client: Production Client                    ┃
┃ ID: 550e8400-e29b-41d4-a716-446655440000    ┃
┃ Expires: Never                               ┃
┃ Rate Limits: 60/min, 1000/hour, 10000/day   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

⚠️ **CRITICAL**: Copy the API key immediately. It cannot be retrieved later!

### Advanced Creation

Create a key with custom settings:

```bash
python manage_api_keys.py create \
  --name "Development Client" \
  --description "Dev team testing environment" \
  --expires 90 \
  --rate-limit-minute 10 \
  --rate-limit-hour 100 \
  --rate-limit-day 1000
```

**Parameters**:
- `--name`: Client name (required)
- `--description`: Optional notes
- `--expires`: Days until expiration (omit for no expiration)
- `--rate-limit-minute`: Requests per minute (default: 60)
- `--rate-limit-hour`: Requests per hour (default: 1000)
- `--rate-limit-day`: Requests per day (default: 10000)

### Key Storage Security

- Keys are **never** stored in plaintext
- Only SHA-256 hashes are stored in the database
- First 8 characters stored as prefix for display
- Lost keys cannot be recovered (only rotated)

## Listing API Keys

### List All Keys

```bash
python manage_api_keys.py list
```

**Output**:
```
╭──────────────────── API Keys (3 total) ────────────────────╮
│ ID        │ Prefix   │ Client Name  │ Status  │ Created    │
├───────────┼──────────┼──────────────┼─────────┼────────────┤
│ 550e84... │ api_abc* │ Production   │ 🟢 Active│ 2025-01-15 │
│ 660f95... │ api_def* │ Development  │ 🟢 Active│ 2025-01-20 │
│ 770g06... │ api_ghi* │ Old Client   │ 🔴 Inactive│ 2024-12-10│
╰────────────────────────────────────────────────────────────╯
```

### Filter Keys

Show only active keys:
```bash
python manage_api_keys.py list --active-only
```

Show only expired keys:
```bash
python manage_api_keys.py list --expired-only
```

## Revoking API Keys

### Revoke by ID

```bash
python manage_api_keys.py revoke 550e8400-e29b-41d4-a716-446655440000
```

### Revoke by Name

```bash
python manage_api_keys.py revoke "Production Client"
```

### Add Revocation Reason

```bash
python manage_api_keys.py revoke "Old Client" --reason "Security audit - key compromised"
```

**Effect**:
- Key immediately becomes invalid
- All future requests with this key will fail with 401
- Usage history is preserved for audit purposes

## Rotating API Keys

Rotation creates a new key and revokes the old one atomically.

### Basic Rotation

```bash
python manage_api_keys.py rotate "Production Client"
```

**Output**:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🔄 Rotated                                   ┃
┠──────────────────────────────────────────────┨
┃ API Key Rotated Successfully!                ┃
┃                                              ┃
┃ New API Key: new_abc123...xyz789             ┃
┃ Client: Production Client                    ┃
┃ New ID: 660f9500-...                         ┃
┃ Old ID: 550e8400-... (revoked)               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Use Cases**:
- Regular security rotation (e.g., every 90 days)
- Suspected key compromise
- Team member departure
- Client migration

**Benefits**:
- Preserves all settings (rate limits, metadata)
- Maintains usage history under same client name
- Zero-downtime rotation (update client before old key expires)

## Monitoring Usage

### View Recent Usage

Show last 7 days:
```bash
python manage_api_keys.py usage "Production Client"
```

Show last 30 days:
```bash
python manage_api_keys.py usage "Production Client" --days 30
```

**Output**:
```
╭────────────── Usage Statistics for 'Production Client' (Last 7 days) ──────────────╮
│ Date       │ Total Requests │ Successful │ Failed │ Avg Response (ms) │
├────────────┼────────────────┼────────────┼────────┼───────────────────┤
│ 2025-01-20 │ 1,247         │ 1,245      │ 2      │ 125.4            │
│ 2025-01-19 │ 1,089         │ 1,087      │ 2      │ 132.1            │
│ 2025-01-18 │ 956           │ 954        │ 2      │ 118.7            │
╰─────────────────────────────────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📊 Summary                                   ┃
┠──────────────────────────────────────────────┨
┃ Total Requests: 7,234                        ┃
┃ Successful: 7,228 (99.9%)                   ┃
┃ Failed: 6                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Usage Tracking Details

The system tracks:
- **Endpoint**: Which MCP endpoint was called
- **Method**: HTTP method (GET, POST, etc.)
- **Status Code**: Response status (200, 401, 429, etc.)
- **IP Address**: Client IP
- **User Agent**: Client software
- **Response Time**: Request duration in milliseconds
- **Timestamp**: Exact request time

### Analytics Queries

For advanced analytics, query the database directly:

```sql
-- Top endpoints by usage
SELECT endpoint, COUNT(*) as request_count
FROM api_key_usage
WHERE api_key_id = 'YOUR_KEY_ID'
GROUP BY endpoint
ORDER BY request_count DESC;

-- Error rate over time
SELECT
  DATE(timestamp) as date,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status_code >= 400) as errors,
  ROUND(COUNT(*) FILTER (WHERE status_code >= 400)::numeric / COUNT(*) * 100, 2) as error_rate
FROM api_key_usage
WHERE api_key_id = 'YOUR_KEY_ID'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

## Rate Limiting

### Default Limits

- **Per Minute**: 60 requests
- **Per Hour**: 1,000 requests
- **Per Day**: 10,000 requests

### Custom Limits

Set custom limits when creating a key:

```bash
python manage_api_keys.py create \
  --name "High-Traffic Client" \
  --rate-limit-minute 200 \
  --rate-limit-hour 5000 \
  --rate-limit-day 50000
```

### Rate Limit Response

When a limit is exceeded, the API returns:

**Status**: `429 Too Many Requests`

**Headers**:
```
X-RateLimit-Reset: 1705763400
Retry-After: 60
```

**Body**:
```json
{
  "error": true,
  "error_type": "rate_limit_exceeded",
  "message": "Rate limit exceeded for minute",
  "retry_after": 60
}
```

### Monitoring Rate Limits

Check rate limit status in the database:

```sql
-- Current request count for last minute
SELECT COUNT(*) FROM api_key_usage
WHERE api_key_id = 'YOUR_KEY_ID'
  AND timestamp >= NOW() - INTERVAL '1 minute';

-- Use the helper function
SELECT * FROM check_rate_limit(
  'YOUR_KEY_ID',  -- API key ID
  'minute',       -- Period: 'minute', 'hour', or 'day'
  60              -- Limit
);
```

## Maintenance

### Cleanup Old Keys

Delete inactive keys older than 90 days:

```bash
python manage_api_keys.py cleanup --days 90
```

**Interactive Confirmation**:
```
Found 5 keys to delete:
  - Old Client 1 (ID: 770g06...)
  - Old Client 2 (ID: 880h17...)
  ...

Delete these 5 keys? (yes/no):
```

### Deactivate Expired Keys

Run periodically (or set up as cron job):

```sql
SELECT deactivate_expired_api_keys();
```

Returns the number of keys deactivated.

### Database Cleanup

Clean up old usage records (keep last 90 days):

```sql
DELETE FROM api_key_usage
WHERE timestamp < NOW() - INTERVAL '90 days';
```

**Recommendation**: Run monthly to keep database size manageable.

## Troubleshooting

### "Invalid API key" Error

**Problem**: Client receives 401 Unauthorized

**Possible Causes**:
1. Key typed incorrectly
2. Key has expired
3. Key has been revoked
4. Wrong Authorization header format

**Solution**:
```bash
# Check key status
python manage_api_keys.py list

# If expired or revoked, rotate
python manage_api_keys.py rotate "Client Name"

# Verify header format
Authorization: Bearer <api_key>
```

### "Rate limit exceeded" Error

**Problem**: Client receives 429 Too Many Requests

**Solution**:
```bash
# Check usage patterns
python manage_api_keys.py usage "Client Name" --days 1

# Increase limits if legitimate
python manage_api_keys.py create \
  --name "Client Name (New)" \
  --rate-limit-minute 200

# Then revoke old key
python manage_api_keys.py revoke "Client Name (Old)"
```

### Missing Usage Data

**Problem**: Usage statistics are empty

**Possible Causes**:
1. Database mode not enabled
2. No requests made yet
3. Logging failed silently

**Solution**:
```bash
# Verify database mode is enabled
grep MCP_API_AUTH_DB_ENABLED .env

# Check database connection
python -c "from api_key_auth_db import *; print('Connection OK')"

# Verify usage table
psql> SELECT COUNT(*) FROM api_key_usage;
```

### Performance Issues

**Problem**: Authentication is slow

**Solutions**:
1. **Cache cleared too often**: Cache TTL is 5 minutes
2. **Database queries slow**: Check indexes exist
3. **Too many usage records**: Run cleanup

```sql
-- Verify indexes
SELECT indexname FROM pg_indexes
WHERE tablename IN ('api_keys', 'api_key_usage');

-- Check query performance
EXPLAIN ANALYZE
SELECT * FROM api_keys WHERE key_hash = 'abc123...';
```

## Best Practices

### Security

1. **Never commit API keys to git**
   - Add `.env` to `.gitignore`
   - Use `.env.example` for templates only

2. **Rotate keys regularly**
   - Every 90 days for production
   - After team member departure
   - After suspected compromise

3. **Use descriptive names**
   - Good: "Production API - Main Server"
   - Bad: "Key 1"

4. **Set expiration dates**
   - Temporary clients: 30-90 days
   - Production: 365 days
   - Development: 7-30 days

### Monitoring

1. **Review usage weekly**
   ```bash
   python manage_api_keys.py usage "Client" --days 7
   ```

2. **Set up alerts** for unusual patterns:
   - Sudden spike in requests
   - High error rates
   - Rate limit violations

3. **Archive old keys**
   ```bash
   python manage_api_keys.py cleanup --days 90
   ```

### Rate Limiting

1. **Start conservative**
   - Begin with default limits
   - Increase based on actual usage

2. **Monitor rate limit hits**
   ```sql
   SELECT COUNT(*) FROM api_key_usage
   WHERE status_code = 429;
   ```

3. **Communicate limits to clients**
   - Document in API documentation
   - Include in onboarding materials

## Advanced Usage

### Batch Operations

Create multiple keys from a CSV:

```bash
# keys.csv
# name,description,expires,rate_limit_minute
# Client A,Production,365,100
# Client B,Development,30,10

while IFS=, read -r name desc expires limit; do
  python manage_api_keys.py create \
    --name "$name" \
    --description "$desc" \
    --expires "$expires" \
    --rate-limit-minute "$limit"
done < keys.csv
```

### Programmatic Access

Use the API directly in Python:

```python
from api_key_auth_db import create_api_key_db
from supabase import create_client
import os

# Initialize
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)
db = create_api_key_db(supabase)

# Validate key
is_valid, key_record = db.validate_api_key("api_key_here")

# Check rate limit
is_ok, period, reset = db.check_rate_limit(
    key_record["id"],
    key_record
)

# Get usage stats
stats = db.get_usage_stats(key_record["id"], days=7)
```

## Support

For issues or questions:
1. Check this documentation
2. Review server logs: `tail -f legal_rag_server.log`
3. Check Supabase logs in dashboard
4. Open GitHub issue with details

## Changelog

- **2025-01-20**: Added database-backed authentication (Phase 2)
- **2025-01-15**: Initial environment variable authentication (Phase 1)
