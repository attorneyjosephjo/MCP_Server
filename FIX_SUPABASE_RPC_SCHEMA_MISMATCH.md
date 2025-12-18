# Fix: Supabase RPC Function Schema Mismatch

**Date:** 2025-12-19
**File Modified:** `legal_rag_utils.py`
**Function:** `search_documents_with_rerank()`

---

## Problem

When AI agents used the MCP server's semantic search tool, they encountered this error:

```json
{
  "error": true,
  "error_type": "search_error",
  "message": "Search failed: {'message': 'Could not find the function public.match_n8n_law_startuplaw(match_count, match_threshold, query_embedding) in the schema cache', 'code': 'PGRST202', 'hint': 'Perhaps you meant to call the function public.match_n8n_law_startuplaw(filter, match_count, query_embedding)'}"
}
```

### Root Cause

The Python code was calling the Supabase RPC function with incorrect parameters:

| Parameter Position | Code Called | Supabase Expected |
|--------------------|-------------|-------------------|
| 1st | `match_threshold` | `filter` |
| 2nd | `match_count` | `match_count` |
| 3rd | `query_embedding` | `query_embedding` |

---

## Solution

### Before (Incorrect)

```python
# legal_rag_utils.py - lines 295-302
return supabase.rpc(
    config.match_function,
    {
        'query_embedding': query_embedding,
        'match_threshold': config.match_threshold,  # WRONG
        'match_count': search_count
    }
).execute()
```

### After (Fixed)

```python
# legal_rag_utils.py - lines 295-307
# Build filter for document type if provided
filter_param = {}
if document_type:
    filter_param = {'legaldocument_type': document_type}

return supabase.rpc(
    config.match_function,
    {
        'query_embedding': query_embedding,
        'filter': filter_param,  # CORRECT
        'match_count': search_count
    }
).execute()
```

---

## Changes Made

1. **Removed** `match_threshold` parameter (not supported by Supabase function)
2. **Added** `filter` parameter as a JSONB object
3. **Improved filtering** - Document type filtering now happens at database level instead of post-filtering in Python

---

## Filter Parameter Format

The `filter` parameter accepts a JSONB object to filter results:

```python
# No filter (search all documents)
filter_param = {}

# Filter by document type
filter_param = {'legaldocument_type': 'practice_notes_checklists'}
```

### Valid `legaldocument_type` Values

- `practice_notes_checklists`
- `standard_documents_clauses`
- `cases`
- `laws_regulations`

---

## Testing

After this fix, the semantic search should work correctly:

```json
{
  "tool": "semantic_search_legal_documents",
  "query": "What is SAFEs?",
  "top_k": 5,
  "document_type": "practice_notes_checklists"
}
```

Expected: Returns relevant legal documents instead of schema mismatch error.

---

# Fix: Document Identification Using notebook_id Instead of Chunk ID

**Date:** 2025-12-19
**Files Modified:** `legal_rag_utils.py`, `legal_rag_server.py`
**Functions:** `get_document()`, `list_documents()`

---

## Problem

The original implementation used chunk `id` (int8) to identify documents, but this was incorrect because:

1. Each document is split into multiple **chunks** in the database
2. The `id` field is just the **chunk ID**, not the document ID
3. Using chunk ID would only return a single chunk, not the full document

### Correct Document Structure

```json
{
  "id": 12345,                    // Chunk ID (NOT unique per document)
  "notebook_id": "gcGicGiHO59...", // Document ID (unique per document)
  "doc_name": "Articles of Organization (CA).pdf",
  "content": "chunk content here..."
}
```

A single document may have many chunks (e.g., IDs 12345, 12346, 12347) all sharing the same `notebook_id`.

---

## Solution

### 1. `get_document()` - Now Uses notebook_id

**Before (Incorrect):**
```python
def get_document(document_id: str, config):
    # Returns only ONE chunk
    result = supabase.table(config.table_name) \
        .select('*') \
        .eq('id', document_id) \
        .execute()
```

**After (Fixed):**
```python
def get_document(notebook_id: str, config):
    # Returns ALL chunks for the document, combined
    result = supabase.table(config.table_name) \
        .select('*') \
        .eq('metadata->>notebook_id', notebook_id) \
        .order('metadata->loc->lines->>from') \
        .execute()

    # Combine all chunks' content in order
    combined_content = "\n\n".join([chunk['content'] for chunk in chunks])
```

### 2. `list_documents()` - Now Groups by notebook_id

**Before (Incorrect):**
- Listed individual chunks (same document appeared multiple times)
- Returned chunk IDs

**After (Fixed):**
- Groups chunks by `notebook_id` to get unique documents
- Returns `notebook_id` for each document
- Shows `chunk_count` indicating how many chunks per document
- Combines content when `include_content=True`

---

## API Changes

### `get_legal_document_by_id` Tool

| Attribute | Before | After |
|-----------|--------|-------|
| Parameter | `document_id` (int) | `notebook_id` (string) |
| Returns | Single chunk | All chunks combined |
| Example | `"12345"` | `"gcGicGiHO59qebbbgcGicGiHO59qebbbgcGi"` |

### `list_all_legal_documents` Tool

| Attribute | Before | After |
|-----------|--------|-------|
| Lists | Chunks | Unique documents |
| Identifier | `id` (chunk) | `notebook_id` (document) |
| New field | - | `chunk_count` |
| Content | One chunk | All chunks combined |

---

## Response Format Examples

### `get_legal_document_by_id` Response

```json
{
  "notebook_id": "gcGicGiHO59qebbbgcGicGiHO59qebbbgcGi",
  "doc_name": "Articles of Organization (CA).pdf",
  "total_chunks": 5,
  "content": "Full combined document content...",
  "metadata": { ... },
  "chunk_ids": [12345, 12346, 12347, 12348, 12349],
  "retrieved_at": "2025-12-19 10:30:00"
}
```

### `list_all_legal_documents` Response

```json
{
  "total_documents": 150,
  "page_size": 50,
  "offset": 0,
  "documents": [
    {
      "notebook_id": "gcGicGiHO59qebbbgcGicGiHO59qebbbgcGi",
      "doc_name": "Articles of Organization (CA).pdf",
      "legaldocument_type": "practice_notes_checklists",
      "chunk_count": 5,
      "summary": "This Practice Note outlines the requirements...",
      "jurisdiction": "united_states_california"
    }
  ]
}
```

---

## Related Files

- `legal_rag_utils.py` - Contains the fixed `search_documents_with_rerank()`, `get_document()`, and `list_documents()` functions
- `legal_rag_server.py` - MCP server that exposes the search tools
- `DATABASE_SCHEMA_ALIGNMENT_PROMPT.md` - Database schema documentation
