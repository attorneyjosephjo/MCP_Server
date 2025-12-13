# Database Schema Alignment Prompt Template

Use this prompt template when building RAG systems with MCP servers to ensure code accurately reflects your database structure.

---

## Prompt Template

```markdown
I'm building a RAG (Retrieval-Augmented Generation) system with an MCP server. Please ensure the code accurately reflects my database structure.

### Database Information

**Table Name:** [your_table_name]
**Database Type:** Supabase PostgreSQL

### Table Columns

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| id | int8 | Primary key, auto-incrementing integer (NOT UUID) |
| content | text | Full text content of the document |
| metadata | jsonb | JSON object containing document metadata |
| embedding | vector | Vector embeddings for semantic search |
| fts | tsvector | Full-text search vector |

### Metadata JSON Structure

The `metadata` column contains a JSONB object with the following structure:

```json
{
  "loc": {
    "lines": {
      "from": 1,
      "to": 6
    }
  },
  "hash": "string",
  "doc_id": "string",
  "doc_name": "string",
  "doc_type": "string",
  "language": "string",
  "file_path": "string",
  "record_id": "string",
  "notebook_id": "string",
  "file_summary": "string",
  "jurisdiction": "string",
  "retrieved_at": "ISO 8601 timestamp",
  "sub_category": "string",
  "main_category": "string",
  "legaldocument_type": "string"
}
```

### Critical Metadata Fields

**Primary Document Type Field:** `metadata->legaldocument_type`

**Valid Values for `legaldocument_type`:**
- `practice_notes_checklists`
- `standard_documents_clauses`
- `cases`
- `laws_regulations`

**Note:** Do NOT use generic field names like `type`, `doc_type`, or assume UUID formats. Use the exact field names as specified above.

### Code Requirements

1. **ID Handling:**
   - Row IDs are `int8` (integers), NOT UUIDs
   - Validation should check for integer format using `str(id).isdigit()`
   - Example valid ID: `"12345"` (string representation of integer)

2. **Metadata Access:**
   - Document type filtering must use: `metadata->>'legaldocument_type'`
   - When querying Supabase, use: `.eq('metadata->>legaldocument_type', document_type)`

3. **Tool/Function Docstrings:**
   - Clearly specify that `document_type` accepts the exact values listed above
   - Show integer ID examples in documentation, not UUID examples

4. **Response Format:**
   - Always return the `legaldocument_type` field when including document metadata
   - Extract document type using: `doc['metadata'].get('legaldocument_type')`

### Example Query Patterns

**Filter by document type:**
```python
supabase.table(table_name) \
    .select('id, content, metadata') \
    .eq('metadata->>legaldocument_type', 'practice_notes_checklists') \
    .execute()
```

**Get document by ID:**
```python
supabase.table(table_name) \
    .select('*') \
    .eq('id', 12345) \  # Integer, not UUID
    .execute()
```

### Additional Context

- **Vector Search Function:** `match_[table_name]` (RPC function in Supabase)
- **Embedding Model:** text-embedding-3-small (1536 dimensions)
- **Reranking Model:** Cohere rerank-v3.5

Please review this schema and ensure ALL code accurately reflects:
1. Integer IDs (int8), not UUIDs
2. The exact metadata field name `legaldocument_type`
3. The four valid document type values
4. Proper JSONB querying syntax for PostgreSQL/Supabase
```

---

## How to Use This Template

For your next project:

1. **Replace the bracketed placeholders:**
   - `[your_table_name]` → your actual table name
   - Update valid values in "Valid Values for `legaldocument_type`"
   - Modify the metadata structure if different

2. **Add project-specific details:**
   - API keys needed
   - Special business logic
   - Rate limiting requirements
   - Authentication methods

3. **Include this at the start of your conversation** with an AI assistant when building similar systems.

---

## Current Project Example

For reference, here's how this was applied to the legal RAG server:

- **Table Name:** `n8n_law_startuplaw`
- **Vector Search Function:** `match_n8n_law_startuplaw`
- **Document Types:** Practice notes, standard documents, cases, laws/regulations
- **ID Type:** int8 (validated with `str(document_id).isdigit()`)
- **Type Field:** `metadata->>'legaldocument_type'`

This configuration is reflected in:
- `legal_rag_server.py` (tool definitions and docstrings)
- `legal_rag_utils.py` (query logic and validation)
