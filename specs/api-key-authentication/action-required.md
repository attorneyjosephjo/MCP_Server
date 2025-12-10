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

- [ ] **Verify Supabase connection** - Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set in `.env`
- [ ] **Review database migration** - Read `migrations/001_create_api_keys_tables.sql` to understand what will be created

### Database Setup

- [ ] **Run database migration** - Execute `migrations/001_create_api_keys_tables.sql` in Supabase SQL Editor
- [ ] **Verify tables created** - Run query: `SELECT table_name FROM information_schema.tables WHERE table_name IN ('api_keys', 'api_key_usage');`
- [ ] **Verify indexes created** - Run query: `SELECT indexname FROM pg_indexes WHERE tablename IN ('api_keys', 'api_key_usage');`
- [ ] **Test helper functions** - Run query: `SELECT deactivate_expired_api_keys();` (should return 0)

### API Key Creation

- [ ] **Create first API key** - Run: `python manage_api_keys.py create --name "Production Client"`
- [ ] **Save API key securely** - Copy the key immediately (cannot be retrieved later!)
- [ ] **Create test key** - Run: `python manage_api_keys.py create --name "Test Client" --expires 30`
- [ ] **Verify keys in database** - Run: `python manage_api_keys.py list`

### Enable Database Mode

- [ ] **Update .env file** - Set `MCP_API_AUTH_DB_ENABLED=true`
- [ ] **Update Coolify environment** - Add `MCP_API_AUTH_DB_ENABLED=true` to deployment platform

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

## Support

For detailed documentation, see:
- `implementation-plan.md` - Complete implementation guide
- `docs/API_KEY_MANAGEMENT.md` - Comprehensive API key management guide
- `requirements.md` - Feature requirements and architecture

---

> **Note:** These tasks are also listed in context within `implementation-plan.md`. This file provides a focused checklist of manual steps required for deployment and testing.
