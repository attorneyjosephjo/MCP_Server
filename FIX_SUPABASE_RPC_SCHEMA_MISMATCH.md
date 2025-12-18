# Legal RAG MCP Server - Bug Fixes & Updates

**Date:** 2025-12-19
**Version:** Post-fix
**Deployment URL:** `https://startuplawrag.thejolawfirm.uk/mcp`

---

## Table of Contents

1. [Fix #1: Supabase RPC Schema Mismatch](#fix-1-supabase-rpc-schema-mismatch)
2. [Fix #2: Document Identification (notebook_id)](#fix-2-document-identification-using-notebook_id)
3. [Understanding the Search Pipeline](#understanding-the-search-pipeline)
4. [API Reference](#api-reference)
5. [Database Schema](#database-schema)

---

# Fix #1: Supabase RPC Schema Mismatch

**Files Modified:** `legal_rag_utils.py`
**Function:** `search_documents_with_rerank()`

## Problem

When AI agents used the MCP server's semantic search tool, they encountered this error:

```json
{
  "error": true,
  "error_type": "search_error",
  "message": "Search failed: {'message': 'Could not find the function public.match_n8n_law_startuplaw(match_count, match_threshold, query_embedding) in the schema cache', 'code': 'PGRST202', 'hint': 'Perhaps you meant to call the function public.match_n8n_law_startuplaw(filter, match_count, query_embedding)'}"
}
```

## Root Cause

The Python code was calling the Supabase RPC function with incorrect parameters:

| Parameter | Code Called (Wrong) | Supabase Expected (Correct) |
|-----------|---------------------|----------------------------|
| 1st | `match_threshold` | `filter` |
| 2nd | `match_count` | `match_count` |
| 3rd | `query_embedding` | `query_embedding` |

## Solution

### Before (Incorrect)

```python
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

## Filter Parameter Format

The `filter` parameter accepts a JSONB object:

```python
# No filter (search all documents)
filter_param = {}

# Filter by document type
filter_param = {'legaldocument_type': 'practice_notes_checklists'}
```

### Valid `legaldocument_type` Values

| Value | Description |
|-------|-------------|
| `practice_notes_checklists` | Practice guides, checklists, how-to documents |
| `standard_documents_clauses` | Templates, standard clauses, form documents |
| `cases` | Case law, court decisions |
| `laws_regulations` | Statutes, regulations, legal codes |

---

# Fix #2: Document Identification Using notebook_id

**Files Modified:** `legal_rag_utils.py`, `legal_rag_server.py`
**Functions:** `get_document()`, `list_documents()`

## Problem

The original implementation used chunk `id` (int8) to identify documents, but this was incorrect because:

1. Each document is split into multiple **chunks** in the database
2. The `id` field is just the **chunk ID**, not the document ID
3. Using chunk ID would only return a single chunk, not the full document

## Database Structure

```
Document: "Articles of Organization (CA).pdf"
├── Chunk 1 (id: 12345, notebook_id: "gcGicGiHO59...")
├── Chunk 2 (id: 12346, notebook_id: "gcGicGiHO59...")
├── Chunk 3 (id: 12347, notebook_id: "gcGicGiHO59...")
└── Chunk 4 (id: 12348, notebook_id: "gcGicGiHO59...")
                          ↑
                  Same notebook_id for all chunks
```

## Solution

### `get_document()` - Now Uses notebook_id

**Before:** Returns only ONE chunk by integer ID
**After:** Returns ALL chunks combined by notebook_id

```python
def get_document(notebook_id: str, config):
    result = supabase.table(config.table_name) \
        .select('*') \
        .eq('metadata->>notebook_id', notebook_id) \
        .order('metadata->loc->lines->>from') \
        .execute()

    # Combine all chunks' content in order
    combined_content = "\n\n".join([chunk['content'] for chunk in chunks])
```

### `list_documents()` - Now Groups by notebook_id

**Before:** Listed individual chunks (duplicates)
**After:** Lists unique documents grouped by notebook_id

## API Changes Summary

| Tool | Parameter Change | Returns |
|------|------------------|---------|
| `get_legal_document_by_id` | `document_id` (int) → `notebook_id` (string) | All chunks combined |
| `list_all_legal_documents` | No change | Unique documents with `chunk_count` |

---

# Understanding the Search Pipeline

## How Semantic Search Works

```
User Query: "What is SAFEs?"
            ↓
┌─────────────────────────────────────────────────────┐
│ Step 1: Generate Embedding                          │
│ - Model: text-embedding-3-small (OpenAI)            │
│ - Converts query to 1536-dimension vector           │
└─────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: Vector Search (Supabase RPC)                │
│ - Function: match_n8n_law_startuplaw                │
│ - Retrieves 15 candidate CHUNKS                     │
│ - Uses cosine similarity on embeddings              │
│ - Optional: Filter by legaldocument_type            │
└─────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: Cohere Rerank                               │
│ - Model: rerank-v3.5                                │
│ - Reranks chunks by semantic relevance to query     │
│ - Returns top 5 most relevant chunks                │
│ - Adds relevance_score (0.0 - 1.0)                  │
└─────────────────────────────────────────────────────┘
            ↓
        Returns top 5 most relevant CHUNKS
        (may be from different documents)
```

## What Gets Reranked?

**Important:** The reranking operates on **chunks**, not full documents.

| Stage | Input | Output |
|-------|-------|--------|
| Vector Search | Query embedding | 15 candidate chunks |
| Rerank | 15 chunks + query | Top 5 chunks with relevance scores |

The returned chunks may come from different documents. Each chunk includes its `notebook_id` so users can retrieve the full document if needed.

---

# API Reference

## Tools Available

### 1. `semantic_search_legal_documents`

Semantic search with vector similarity and Cohere reranking.

```json
{
  "query": "What is SAFEs?",
  "top_k": 5,
  "document_type": "practice_notes_checklists"
}
```

**Response:** Top 5 most relevant chunks with relevance scores.

### 2. `get_legal_document_by_id`

Retrieve a complete document by its notebook_id.

```json
{
  "notebook_id": "gcGicGiHO59qebbbgcGicGiHO59qebbbgcGi"
}
```

**Response:**
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

### 3. `list_all_legal_documents`

List unique documents with pagination.

```json
{
  "limit": 50,
  "offset": 0,
  "include_content": false
}
```

**Response:**
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

### 4. `browse_legal_documents_by_type`

Browse documents filtered by type.

```json
{
  "document_type": "practice_notes_checklists",
  "limit": 20,
  "offset": 0
}
```

---

# Database Schema

## Table: `n8n_law_startuplaw`

| Column | Type | Description |
|--------|------|-------------|
| `id` | int8 | Chunk ID (auto-increment) |
| `content` | text | Chunk text content |
| `metadata` | jsonb | Document metadata |
| `embedding` | vector(1536) | OpenAI embedding |
| `fts` | tsvector | Full-text search vector |

## Metadata Structure

```json
{
  "notebook_id": "gcGicGiHO59qebbbgcGicGiHO59qebbbgcGi",
  "doc_name": "Articles of Organization (CA).pdf",
  "doc_id": "1vNd49VtJqYv9KlT5VLIZzSv_f16tzDhQ",
  "legaldocument_type": "practice_notes_checklists",
  "file_summary": "This Practice Note outlines...",
  "jurisdiction": "united_states_california",
  "main_category": "startuplaw",
  "sub_category": "legal_entity_types_formation",
  "file_path": "https://drive.google.com/...",
  "loc": {
    "lines": { "from": 1, "to": 6 }
  }
}
```

## RPC Function: `match_n8n_law_startuplaw`

**Signature:**
```sql
match_n8n_law_startuplaw(
  filter jsonb,
  match_count int,
  query_embedding vector(1536)
)
```

**Parameters:**
- `filter`: JSONB object for filtering (e.g., `{'legaldocument_type': 'cases'}`)
- `match_count`: Number of results to return
- `query_embedding`: 1536-dimension vector from OpenAI

---

## Related Files

| File | Purpose |
|------|---------|
| `legal_rag_utils.py` | Core search, retrieval, and reranking logic |
| `legal_rag_server.py` | MCP server tool definitions |
| `DATABASE_SCHEMA_ALIGNMENT_PROMPT.md` | Schema documentation template |
