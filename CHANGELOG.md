# Changelog

All notable changes to the Legal RAG MCP Server will be documented in this file.

## [Unreleased]

### Fixed

#### Critical Bug: Missing Import for Database Authentication (2024-12-18)

**File:** `legal_rag_server.py`

**Problem:**
When running the MCP server in HTTP mode with database-backed authentication enabled (`MCP_API_AUTH_DB_ENABLED=true`), the server would crash with:

```
NameError: name 'get_cached_supabase_client' is not defined
```

**Root Cause:**
Two issues on line 263:

1. The function `get_cached_supabase_client` was called but never imported from `legal_rag_utils`
2. The function requires a `config` parameter but was called without any arguments

**Changes Made:**

1. Added `get_cached_supabase_client` to the import statement (lines 5-13):

```python
from legal_rag_utils import (
    LegalRAGConfig,
    search_documents_with_rerank,
    browse_by_type,
    get_document,
    list_documents,
    create_error_response,
    get_cached_supabase_client  # Added
)
```

2. Fixed the function call to pass the required `config` parameter (line 264):

```python
# Before (broken)
supabase_client = get_cached_supabase_client()

# After (fixed)
supabase_client = get_cached_supabase_client(config)
```

**Impact:**
- HTTP mode with database authentication now works correctly
- Server can properly initialize the Supabase client for API key validation and rate limiting

**Testing:**
To verify the fix, run the server in HTTP mode with database auth:

```bash
MCP_API_AUTH_DB_ENABLED=true python legal_rag_server.py --http
```

The server should start without errors and log:
```
Database-backed API key authentication ENABLED
Using Supabase for API key storage, validation, and rate limiting
```
