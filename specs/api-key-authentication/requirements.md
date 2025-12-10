# API Key Authentication - Requirements

## Project Overview

Add API key authentication to the Legal RAG MCP Server to secure remote HTTP access while maintaining local stdio mode as authentication-free. This enables secure deployment on Coolify while preserving ease of use for local development.

## Business Context

### Current Situation
- **Problem**: HTTP endpoints are publicly accessible without authentication
- **Risk**: Unauthorized access to legal document search capabilities
- **Impact**: Security vulnerability for production deployment on Coolify

### Desired State
- HTTP remote access requires valid API key
- Multiple clients can use different API keys
- Local stdio mode remains unchanged (no auth)
- Simple configuration via environment variables

### Success Criteria
- 100% of HTTP endpoints protected (except health checks)
- Zero breaking changes for existing local users
- Performance impact < 1ms per request
- Clear error messages for authentication failures

## User Stories

### US1: API Key Authentication for HTTP Clients
**As a remote client** using the MCP server over HTTP,
**I want** to authenticate with an API key in the request header,
**So that** only authorized clients can access the legal document search.

**Acceptance Criteria**:
- Client provides API key in `Authorization: Bearer <key>` header
- Valid key → request proceeds to MCP handler
- Invalid/missing key → 401 Unauthorized with clear error message
- Health endpoint (`/health`) remains accessible without auth

### US2: Multiple Client Support
**As a system administrator**,
**I want** to configure multiple API keys for different clients,
**So that** I can grant access to multiple authorized users and revoke individual keys.

**Acceptance Criteria**:
- Support comma-separated list of API keys in environment variable
- Each key can be optionally named for identification
- Keys validated using constant-time comparison for security
- Failed auth attempts logged with timestamp

### US3: Local Development Without Auth
**As a developer** using the MCP server locally via stdio,
**I want** to run the server without API key configuration,
**So that** local development remains simple and frictionless.

**Acceptance Criteria**:
- stdio mode (default) requires no authentication
- No environment variables required for local use
- Existing local workflows unchanged

### US4: Clear Configuration and Errors
**As a system administrator**,
**I want** clear documentation and helpful error messages,
**So that** I can easily configure authentication and troubleshoot issues.

**Acceptance Criteria**:
- `.env.example` includes auth configuration with comments
- 401 errors include helpful messages (not security leaks)
- Server startup logs auth status (enabled/disabled)
- Documentation includes key generation examples

## Functional Requirements

### FR1: API Key Validation Middleware

**Requirement**: Implement Starlette middleware to intercept HTTP requests and validate API keys.

**Details**:
- **Middleware Class**: `APIKeyMiddleware` (inherits from `BaseHTTPMiddleware`)
- **Scope**: All HTTP requests in `--http` mode
- **Exempt Endpoints**: `/health`, `/` (root)
- **Protected Endpoints**: All MCP protocol endpoints

**Behavior**:
1. Extract `Authorization` header from request
2. Validate format: `Bearer <api_key>`
3. Compare `<api_key>` against configured keys using `secrets.compare_digest()`
4. If valid: continue to next middleware/handler
5. If invalid/missing: return 401 JSON response

**Error Responses**:
```json
// Missing header
{
  "error": true,
  "error_type": "authentication_error",
  "message": "Missing authentication credentials",
  "details": {
    "required_header": "Authorization",
    "format": "Authorization: Bearer <api_key>"
  }
}

// Invalid key
{
  "error": true,
  "error_type": "authentication_error",
  "message": "Invalid API key"
}
```

### FR2: API Key Configuration

**Requirement**: Load API key configuration from environment variables.

**Configuration Class**: `APIKeyConfig`

**Environment Variables**:
- `MCP_API_AUTH_ENABLED` (required): `true` or `false` (default: `false`)
- `MCP_API_KEYS` (required if enabled): Comma-separated list of valid keys
- `MCP_API_KEY_NAMES` (optional): Comma-separated `key:name` pairs

**Example**:
```bash
MCP_API_AUTH_ENABLED=true
MCP_API_KEYS=abc123,def456,xyz789
MCP_API_KEY_NAMES=abc123:ClientA,def456:ClientB,xyz789:Production
```

**Validation**:
- If `MCP_API_AUTH_ENABLED=true` but `MCP_API_KEYS` is empty → log warning and disable auth
- Keys must be non-empty strings
- Names are optional (used only for logging)

### FR3: Logging and Monitoring

**Requirement**: Log authentication events for security monitoring.

**Log Events**:
1. **Server Startup**:
   - Auth enabled/disabled status
   - Number of configured API keys (not the keys themselves)

2. **Successful Auth**:
   - Client name (if configured)
   - Timestamp
   - Endpoint accessed

3. **Failed Auth**:
   - Reason (missing header, invalid key, wrong format)
   - Timestamp
   - IP address (from request)
   - **Never log the actual API key**

**Log Format** (structured logging):
```
INFO: API Key authentication ENABLED for HTTP mode
INFO: Configured with 3 valid API key(s)
INFO: Authenticated request from "ClientA" to /mcp/v1/tools/list
WARNING: Authentication failed - Invalid API key from 203.0.113.42
```

### FR4: API Key Generation Utility

**Requirement**: Provide a simple script/command to generate secure API keys.

**Implementation**:
```python
# In api_key_auth.py or standalone script
import secrets

def generate_api_key() -> str:
    """Generate a cryptographically secure random API key."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    print(f"Generated API key: {generate_api_key()}")
```

**Usage**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Output Example**:
```
fgW5aAn5B3X-EtCnQittA1jVNKXXThNe8vUZ7DJVL9U
```

### FR5: Selective Endpoint Protection

**Requirement**: Allow certain endpoints to remain public (health checks).

**Public Endpoints** (no auth required):
- `GET /health` - for load balancers and monitoring
- `GET /` - for service discovery

**Protected Endpoints** (auth required):
- All MCP protocol endpoints (`/mcp/*`)
- Any future API endpoints

**Implementation**:
```python
# In APIKeyMiddleware.dispatch()
if request.url.path in ["/health", "/"]:
    return await call_next(request)  # Skip auth
```

## Non-Functional Requirements

### NFR1: Security

**Requirement**: Implement security best practices for API key authentication.

**Security Measures**:
1. **Constant-Time Comparison**: Use `secrets.compare_digest()` to prevent timing attacks
2. **HTTPS Only**: Document requirement for HTTPS in production (Coolify provides this)
3. **Key Length**: Minimum 32 bytes (256 bits of entropy) using `secrets.token_urlsafe(32)`
4. **No Key Logging**: Never log API keys in plaintext
5. **Git Protection**: `.env` file in `.gitignore`, provide `.env.example` only

**Threat Model**:
| Threat | Mitigation |
|--------|------------|
| API key leaked in git | `.env` in `.gitignore` |
| Man-in-the-middle | Require HTTPS (Coolify) |
| Timing attack | `secrets.compare_digest()` |
| Brute force | Long random keys (256 bits) |
| Key rotation | Support multiple keys |

### NFR2: Performance

**Requirement**: Authentication overhead must be negligible.

**Performance Targets**:
- Middleware overhead: < 1ms per request
- Memory overhead: < 5KB total
- No database queries for validation
- Keys loaded once at startup

**Expected Overhead**:
- Extract header: ~0.01ms
- Parse Bearer token: ~0.01ms
- Compare key: ~0.1ms
- **Total: ~0.12ms** (acceptable for 5+ second search queries)

### NFR3: Maintainability

**Requirement**: Code must be simple, testable, and well-documented.

**Implementation Standards**:
- Single file for auth logic (`api_key_auth.py`)
- Clear separation of concerns
- Type hints on all functions
- Docstrings for public APIs

**Code Structure**:
```python
api_key_auth.py
  ├── APIKeyConfig (dataclass)
  ├── APIKeyMiddleware (middleware class)
  ├── validate_api_key() (helper function)
  └── generate_api_key() (utility function)
```

### NFR4: Backward Compatibility

**Requirement**: No breaking changes for existing users.

**Compatibility Requirements**:
- Auth disabled by default (`MCP_API_AUTH_ENABLED=false`)
- stdio mode unchanged (no auth)
- Existing HTTP deployments work without env var changes
- Clear migration path documented

**Migration Strategy**:
1. Deploy code with auth disabled (default)
2. Verify existing functionality works
3. Generate API keys
4. Set `MCP_API_AUTH_ENABLED=true` and `MCP_API_KEYS`
5. Update clients with API keys
6. Monitor logs for auth events

### NFR5: Usability

**Requirement**: Configuration must be simple and well-documented.

**Usability Features**:
- Single environment variable to enable/disable
- Clear `.env.example` with comments
- Helpful error messages (no security leaks)
- Key generation command in docs
- Example curl commands for testing

**Documentation Locations**:
- `.env.example` - inline comments

## Acceptance Criteria

### AC1: Authentication Works
- [ ] HTTP request without API key returns 401
- [ ] HTTP request with invalid API key returns 401
- [ ] HTTP request with valid API key returns 200
- [ ] stdio mode works without API key configuration
- [ ] `/health` endpoint accessible without auth
- [ ] Error messages are clear and helpful

### AC2: Multiple Keys Supported
- [ ] Can configure 3+ API keys via comma-separated list
- [ ] Each key validates independently
- [ ] Can optionally name keys for logging
- [ ] Removing a key from env var revokes access

### AC3: Security Requirements Met
- [ ] Uses constant-time comparison (`secrets.compare_digest()`)
- [ ] API keys never appear in logs
- [ ] `.env` file in `.gitignore`
- [ ] Generated keys have 256 bits of entropy
- [ ] Documentation requires HTTPS for production

### AC4: Performance Requirements Met
- [ ] Authentication overhead < 1ms per request
- [ ] No database queries for validation
- [ ] Keys loaded once at startup
- [ ] Memory overhead < 5KB

### AC5: Backward Compatibility Maintained
- [ ] Auth disabled by default
- [ ] Existing local stdio workflows unchanged
- [ ] Existing HTTP deployments work without changes
- [ ] No breaking changes to API

### AC6: Code Quality Standards
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] Code passes linting (mypy, ruff)

## Out of Scope (Future Enhancements)

The following features are **NOT** included in the initial implementation:

1. **Rate Limiting**: Per-API-key request rate limits
2. **Key Expiration**: Time-based key expiration
3. **Key Metadata Storage**: Database for key usage stats
4. **Admin Dashboard**: Web UI for key management
5. **Webhook Notifications**: Alerts for security events
6. **OAuth/JWT**: More complex authentication protocols
7. **Role-Based Access**: Different permission levels per key

These may be considered for future phases based on user needs.

## Dependencies

### Technical Dependencies
- **Python**: 3.10+ (existing)
- **Starlette**: Included with FastMCP
- **secrets**: Python standard library
- **typing**: Python standard library

### External Dependencies
- None (no new packages required)

### Configuration Dependencies
- `.env` file for API keys
- Coolify for HTTPS termination (production)

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API key leaked in git | Critical | Low | `.env` in `.gitignore`, code review |
| Performance degradation | Medium | Low | Measured overhead (~0.12ms), negligible |
| Misconfiguration | Medium | Medium | Clear docs, startup validation, warnings |
| Breaking existing users | High | Low | Auth disabled by default, backward compatible |
| HTTPS not enabled | Critical | Medium | Document HTTPS requirement clearly |
| Forgot to set API keys | Medium | Medium | Log warning if enabled but no keys |

## Success Metrics

### Functional Success
- 100% of HTTP endpoints protected (except health)
- Zero authentication bypasses in security testing
- All acceptance criteria met

### Performance Success
- Authentication overhead < 1ms (measured)
- No user-reported performance issues

### Adoption Success
- Deployed to production on Coolify
- At least 2 different clients using different API keys
- Zero authentication-related support tickets

## Timeline Estimate

**Phase 1 (Core Authentication)**: 2-3 hours
- Create `api_key_auth.py`
- Modify `legal_rag_server.py`
- Update `.env.example`
- Basic testing

## References

- FastMCP Documentation: https://github.com/jlowin/fastmcp
- Starlette Middleware: https://www.starlette.io/middleware/
- Python secrets module: https://docs.python.org/3/library/secrets.html
- MCP Specification: https://modelcontextprotocol.io/
