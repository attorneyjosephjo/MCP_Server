# Legal Document RAG MCP Server - Requirements

## Project Overview

Create a Model Context Protocol (MCP) server that provides semantic search and document retrieval capabilities for a legal document database stored in Supabase. The server should integrate with Claude Desktop and match the existing n8n workflow configuration.

## Business Requirements

### Purpose
Enable Claude Desktop to query and retrieve legal documents including:
- Practice guides
- Agreement templates
- Clause samples

### User Stories

1. **As a user**, I want to search legal documents using natural language queries so that I can find relevant documents without knowing exact keywords.

2. **As a user**, I want to browse documents by type (practice guides, agreements, clauses) so that I can explore specific categories of legal content.

3. **As a user**, I want to retrieve a specific document by its ID so that I can access the full content of a document I've previously identified.

4. **As a user**, I want to list all available legal documents so that I can see what's in the database.

## Functional Requirements

### FR1: Semantic Search Tool
- **Name**: `semantic_search_legal_documents`
- **Input Parameters**:
  - `query` (string, required): Natural language search query
  - `top_k` (integer, optional, default: 10): Number of results to return
  - `document_type` (string, optional): Filter by type ("practice_guide", "agreement", or "clause")
- **Output**: List of documents with relevance scores, content, and metadata
- **Behavior**:
  - Generate embeddings using OpenAI text-embedding-3-small
  - Perform vector similarity search in Supabase
  - Rerank results using Cohere rerank-v3.5
  - Return top_k most relevant documents

### FR2: Browse by Type Tool
- **Name**: `browse_legal_documents_by_type`
- **Input Parameters**:
  - `document_type` (string, required): "practice_guide", "agreement", or "clause"
  - `limit` (integer, optional, default: 20, max: 100): Documents per page
  - `offset` (integer, optional, default: 0): Pagination offset
- **Output**: Paginated list of documents with summaries
- **Behavior**:
  - Filter documents by metadata type field
  - Return documents with 200-character summaries
  - Include pagination metadata (has_more, count, etc.)

### FR3: Get Document by ID Tool
- **Name**: `get_legal_document_by_id`
- **Input Parameters**:
  - `document_id` (string, required): UUID of the document
- **Output**: Complete document with full content and metadata
- **Behavior**:
  - Validate UUID format
  - Retrieve document from Supabase
  - Return full content or helpful error if not found

### FR4: List All Documents Tool
- **Name**: `list_all_legal_documents`
- **Input Parameters**:
  - `limit` (integer, optional, default: 50, max: 100): Documents per page
  - `offset` (integer, optional, default: 0): Pagination offset
  - `include_content` (boolean, optional, default: false): Include full content
- **Output**: Paginated list of all documents
- **Behavior**:
  - Return all documents with metadata
  - Optionally include full content
  - Provide pagination information (total count, pages, etc.)

## Technical Requirements

### TR1: Technology Stack
- **Language**: Python 3.13
- **MCP Framework**: FastMCP (mcp[cli] >=1.12.2)
- **Database**: Supabase with pgvector extension
- **AI Services**:
  - OpenAI API (text-embedding-3-small for embeddings)
  - Cohere API (rerank-v3.5 for reranking)
- **Package Manager**: UV

### TR2: Data Source
- **Database**: Supabase PostgreSQL with pgvector
- **Table Name**: `n8n_law_startuplaw`
- **Vector Function**: `match_n8n_law_startuplaw` (custom RPC function)
- **Embedding Dimensions**: 1536 (OpenAI text-embedding-3-small)

### TR3: Expected Schema
```sql
CREATE TABLE n8n_law_startuplaw (
    id UUID PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(1536)
);
```

**Metadata Structure**:
```json
{
  "type": "practice_guide" | "agreement" | "clause",
  "title": "Document Title",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z",
  "category": "Contract Law",
  "tags": ["startup", "incorporation"],
  "source_url": "https://...",
  "author": "Law Firm Name"
}
```

### TR4: Configuration
Required environment variables:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role API key
- `OPENAI_API_KEY`: OpenAI API key
- `COHERE_API_KEY`: Cohere API key

Optional environment variables:
- `LEGAL_RAG_TABLE_NAME`: Override table name (default: n8n_law_startuplaw)
- `LEGAL_RAG_MATCH_FUNCTION`: Override match function name
- `LEGAL_RAG_TOP_K`: Default top_k value (default: 10)

### TR5: Architecture
- **Separation of Concerns**:
  - `legal_rag_server.py`: MCP server with tool decorators
  - `legal_rag_utils.py`: Business logic and API integrations
  - `test_legal_rag.py`: Testing script
- **Pattern**: Follow existing `main.py` FastMCP pattern
- **Independence**: Separate MCP server from existing CompanyInfoServer

## Non-Functional Requirements

### NFR1: Performance
- Embedding generation: < 2 seconds
- Vector search: < 1 second
- Reranking: < 2 seconds
- Total query time: < 5 seconds

### NFR2: Reliability
- API failures: Retry with exponential backoff (max 3 attempts)
- Cohere failure: Fall back to vector similarity scores
- Configuration errors: Fail fast on startup with clear messages

### NFR3: Error Handling
- Standardized error response format
- Helpful error messages for users
- Validation of all inputs
- Graceful degradation when services fail

### NFR4: Security
- Use Supabase service role key (backend only)
- Never expose credentials in client/logs
- Validate UUID formats to prevent injection
- Use HTTPS for all API calls

### NFR5: Usability
- Clear tool descriptions for Claude Desktop
- Helpful examples in docstrings
- Pagination for large result sets
- Document summaries for quick browsing

## Integration Requirements

### IR1: n8n Workflow Compatibility
- Match existing n8n configuration:
  - Same table name: `n8n_law_startuplaw`
  - Same match function: `match_n8n_law_startuplaw`
  - Same embedding model: OpenAI text-embedding-3-small
  - Same reranker: Cohere rerank-v3.5
  - Same top_k: 10 results

### IR2: Claude Desktop Integration
- Install via: `uv run mcp install legal_rag_server.py`
- Tools appear in Claude Desktop tool panel
- Support natural language queries from users
- Return results in markdown-friendly format

### IR3: Existing Project Integration
- Add dependencies to existing `pyproject.toml`
- Update `.env.example` with new variables
- No conflicts with existing `main.py` server
- Follow existing project conventions

## Testing Requirements

### Testing Strategy
1. **Unit Tests**: Test each utility function independently
2. **Integration Tests**: Test with real API calls via `test_legal_rag.py`
3. **MCP Tests**: Test with `uv run mcp dev legal_rag_server.py`
4. **E2E Tests**: Test with Claude Desktop

### Test Cases
- Semantic search with valid query returns results
- Semantic search with document_type filter works
- Browse by type returns correct document types
- Get by ID retrieves correct document
- Get by ID with invalid UUID returns validation error
- List all returns paginated results
- List all with include_content=true returns full content
- API failures trigger retries
- Cohere failure falls back to vector scores
- Missing environment variables fail on startup

## Constraints

### C1: Existing Infrastructure
- Must work with existing Supabase database
- Cannot modify database schema
- Cannot change existing vector function
- Must use existing API credentials

### C2: Development Environment
- Windows environment (win32)
- Python 3.13
- UV package manager
- Git repository (not remote)

### C3: Dependencies
- Must use FastMCP framework
- Must use official client libraries (Supabase, OpenAI, Cohere)
- Minimize additional dependencies

## Success Criteria

1. All 4 tools successfully installed in Claude Desktop
2. Semantic search returns relevant results with < 5 second response time
3. Document type filtering works correctly
4. Pagination works for all list operations
5. Error handling provides helpful messages
6. Test script validates all functions
7. Documentation is complete and clear
8. Code follows existing project patterns

## Out of Scope

The following features are **not** included in this phase:
- Document upload/creation via MCP
- Document editing/updating
- Document deletion
- Advanced filtering (date ranges, multiple tags)
- Citation generation
- Document comparison
- Export to PDF/Word
- Usage analytics/logging
- Caching layer (Redis)
- Rate limiting (beyond API-level)

These may be considered for future enhancements.

## Acceptance Criteria

- [ ] All 4 MCP tools are implemented and functional
- [ ] Tools can be installed to Claude Desktop via `uv run mcp install`
- [ ] Semantic search returns relevant results with reranking
- [ ] Document type filtering correctly filters results
- [ ] Get by ID retrieves correct documents
- [ ] List all provides accurate pagination
- [ ] Error handling works for all error scenarios
- [ ] Test script passes all tests
- [ ] Code follows existing project structure and patterns
- [ ] Documentation (requirements.md, implementation-plan.md) is complete
- [ ] Environment variables are documented in .env.example
- [ ] No breaking changes to existing MCP server (main.py)
