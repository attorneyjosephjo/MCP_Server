# Legal Document RAG MCP Server - Architecture Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [File-by-File Explanation](#file-by-file-explanation)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [API Integration Flow](#api-integration-flow)
6. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### What This Application Does
This is a **Legal Document Retrieval-Augmented Generation (RAG) Server** that uses the Model Context Protocol (MCP) to provide intelligent legal document search capabilities to Claude Desktop and other MCP clients.

**Key Features:**
- 🔍 **Semantic Search**: Natural language search using AI-powered embeddings
- 📚 **Document Browsing**: Filter and browse by document type
- 🎯 **Precise Retrieval**: Get specific documents by ID
- 📋 **List Management**: Paginated listing of all documents

**Technology Stack:**
- **Protocol**: MCP (Model Context Protocol)
- **Framework**: FastMCP
- **Database**: Supabase with pgvector extension
- **AI Services**: OpenAI (embeddings) + Cohere (reranking)
- **Language**: Python 3.13
- **Deployment**: Docker + Coolify

---

## Architecture Diagrams

### 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  Claude Desktop  │         │  Other MCP       │             │
│  │                  │         │  Clients         │             │
│  └────────┬─────────┘         └────────┬─────────┘             │
│           │                            │                        │
│           └────────────┬───────────────┘                        │
│                        │ MCP Protocol (stdio/HTTP)              │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │         legal_rag_server.py (FastMCP Server)              │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │  🔧 Tool 1: semantic_search_legal_documents         │  │ │
│  │  │  🔧 Tool 2: browse_legal_documents_by_type          │  │ │
│  │  │  🔧 Tool 3: get_legal_document_by_id                │  │ │
│  │  │  🔧 Tool 4: list_all_legal_documents                │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────┬─────────────────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │       legal_rag_utils.py (Business Logic)                 │ │
│  │  • Configuration Management (LegalRAGConfig)              │ │
│  │  • Supabase Client (cached)                               │ │
│  │  • OpenAI Embeddings                                      │ │
│  │  • Cohere Reranking                                       │ │
│  │  • Core Functions (search, browse, get, list)            │ │
│  │  • Error Handling & Retry Logic                          │ │
│  └─────┬──────────────┬──────────────┬────────────────────────┘ │
└────────┼──────────────┼──────────────┼──────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐        │
│  │   Supabase   │  │   OpenAI     │  │    Cohere     │        │
│  │   Database   │  │     API      │  │     API       │        │
│  │  (pgvector)  │  │ (Embeddings) │  │  (Reranking)  │        │
│  └──────────────┘  └──────────────┘  └───────────────┘        │
│  • Vector Store    • text-embedding  • rerank-v3.5            │
│  • Document DB       -3-small        • Relevance Scoring      │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Semantic Search Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  SEMANTIC SEARCH FLOW                            │
└─────────────────────────────────────────────────────────────────┘

User Query: "How to structure a SAFE agreement?"
     │
     ▼
┌──────────────────────────────────────────────┐
│ Step 1: QUERY EMBEDDING                      │
│ Function: generate_embedding_async()         │
│                                              │
│ Input:  "How to structure a SAFE agreement?" │
│ API:    OpenAI text-embedding-3-small       │
│ Output: [0.234, -0.567, 0.123, ... ]        │
│         (1536-dimensional vector)            │
│ Time:   ~1.5 seconds                        │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Step 2: VECTOR SIMILARITY SEARCH             │
│ Function: Supabase RPC match_n8n_law...     │
│                                              │
│ Input:  query_embedding, threshold=0.5      │
│ Action: Compare with all document vectors   │
│         using cosine similarity              │
│ Output: Top 20 similar documents            │
│         with similarity scores               │
│ Time:   ~1.6 seconds                        │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Step 3: FILTER BY TYPE (Optional)            │
│                                              │
│ Input:  document_type = "agreement"         │
│ Action: Filter results where               │
│         metadata.type == "agreement"        │
│ Output: Filtered list of documents          │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Step 4: RERANKING WITH AI                   │
│ Function: rerank_documents_async()          │
│                                              │
│ Input:  Query + Document content            │
│ API:    Cohere rerank-v3.5                 │
│ Action: Deep semantic understanding         │
│         Re-score relevance                  │
│ Output: Top 10 most relevant docs          │
│         with relevance_score (0.0-1.0)     │
│ Time:   ~0.7 seconds                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Step 5: RETURN RESULTS                      │
│                                              │
│ Output: {                                   │
│   "query": "...",                           │
│   "total_results": 10,                      │
│   "results": [                              │
│     {                                       │
│       "id": "uuid",                         │
│       "content": "...",                     │
│       "metadata": {...},                    │
│       "relevance_score": 0.92              │
│     }, ...                                  │
│   ]                                         │
│ }                                           │
│                                              │
│ Total Time: ~5.7 seconds                    │
└──────────────────────────────────────────────┘
```

### 3. Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    COMPONENT RELATIONSHIPS                      │
└────────────────────────────────────────────────────────────────┘

legal_rag_server.py                    legal_rag_utils.py
┌─────────────────────┐              ┌─────────────────────┐
│ FastMCP Server      │              │ LegalRAGConfig      │
│                     │◄─────uses────│ - supabase_url      │
│ @mcp.tool()         │              │ - openai_api_key    │
│ decorators          │              │ - cohere_api_key    │
└──────────┬──────────┘              │ - table_name        │
           │                         │ - match_function    │
           │                         └──────────┬──────────┘
           │                                    │
           │                                    │
           ├────────────────────────────────────┤
           │                                    │
           ▼                                    ▼
┌──────────────────────┐            ┌─────────────────────────┐
│ Tool Functions       │            │ Core Functions          │
│                      │            │                         │
│ • semantic_search... │───calls──►│ • search_documents...   │
│ • browse_...         │───calls──►│ • browse_by_type()      │
│ • get_...            │───calls──►│ • get_document()        │
│ • list_...           │───calls──►│ • list_documents()      │
└──────────────────────┘            └──────────┬──────────────┘
                                               │
           ┌───────────────────────────────────┼────────────┐
           │                                   │            │
           ▼                                   ▼            ▼
┌────────────────────┐      ┌──────────────────────┐  ┌──────────────┐
│ generate_embedding │      │ rerank_documents     │  │ get_supabase │
│ _async()           │      │ _async()             │  │ _client()    │
│                    │      │                      │  │              │
│ Uses: AsyncOpenAI  │      │ Uses: Cohere ClientV2│  │ Uses: create │
│       (async with) │      │       (in thread)    │  │ _client()    │
└─────────┬──────────┘      └──────────┬───────────┘  └──────┬───────┘
          │                            │                     │
          │                            │                     │
          ▼                            ▼                     ▼
┌───────────────┐      ┌─────────────────────┐    ┌──────────────────┐
│ OpenAI API    │      │ Cohere API          │    │ Supabase API     │
│ embeddings    │      │ rerank              │    │ RPC + SELECT     │
└───────────────┘      └─────────────────────┘    └──────────────────┘
```

---

## File-by-File Explanation

### 📄 `legal_rag_server.py` - The MCP Server Interface

**Purpose**: This is the main entry point that exposes 4 tools to MCP clients.

**Key Components:**

```python
# Server Initialization
mcp = FastMCP("LegalDocumentRAGServer")
config = LegalRAGConfig.from_env()  # Load API keys
```

**4 MCP Tools:**

1. **`@mcp.tool() semantic_search_legal_documents()`**
   - **What it does**: Searches legal documents using natural language
   - **Parameters**: 
     - `query` (str): Your search question
     - `top_k` (int): How many results (default 10)
     - `document_type` (str): Filter by type
   - **Example**: `"How to incorporate a Delaware C-corp?"`
   - **Returns**: Ranked list with relevance scores

2. **`@mcp.tool() browse_legal_documents_by_type()`**
   - **What it does**: Browse documents by category
   - **Parameters**:
     - `document_type`: "practice_guide" | "agreement" | "clause"
     - `limit`: Results per page (default 20)
     - `offset`: For pagination
   - **Use Case**: Exploring all agreement templates

3. **`@mcp.tool() get_legal_document_by_id()`**
   - **What it does**: Retrieve full document by UUID
   - **Parameters**: `document_id` (UUID string)
   - **Use Case**: Getting complete content after seeing search results

4. **`@mcp.tool() list_all_legal_documents()`**
   - **What it does**: List all documents with pagination
   - **Parameters**:
     - `limit`: Results per page (default 50)
     - `offset`: For pagination
     - `include_content`: Include full text (default False)
   - **Use Case**: Database overview and management

**Running Modes:**

```python
# Stdio mode (local Claude Desktop)
python legal_rag_server.py

# HTTP mode (remote deployment via Coolify)
python legal_rag_server.py --http
```

**Important Features:**
- ✅ Validates all inputs (query length, top_k range, UUID format)
- ✅ Comprehensive error handling with helpful messages
- ✅ Standardized error response format
- ✅ Health check endpoint at `/health`
- ✅ Root endpoint at `/` with server info

---

### 📄 `legal_rag_utils.py` - The Business Logic Engine

**Purpose**: Contains all the core functionality, API integrations, and configuration.

#### Class: `LegalRAGConfig`

**What it does**: Manages all configuration from environment variables

```python
@dataclass
class LegalRAGConfig:
    supabase_url: str              # Your Supabase project URL
    supabase_key: str              # Service role key
    openai_api_key: str            # OpenAI API key
    cohere_api_key: str            # Cohere API key
    table_name: str = "n8n_law_startuplaw"
    match_function: str = "match_n8n_law_startuplaw"
    top_k: int = 10
    embedding_model: str = "text-embedding-3-small"
    rerank_model: str = "rerank-v3.5"
    match_threshold: float = 0.5
```

**Key Methods:**
- `from_env()`: Loads config from `.env` file
- `validate()`: Ensures all values are valid

---

#### Function: `generate_embedding_async(text, config)`

**What it does**: Converts text to 1536-dimensional vector using OpenAI

**Flow:**
```python
async with AsyncOpenAI(api_key=config.openai_api_key) as client:
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding  # [0.234, -0.567, ...]
```

**Why async with context manager?**
- ✅ Properly closes HTTP connections
- ✅ Prevents 240-second timeout wait
- ✅ Non-blocking execution

**Cost**: ~$0.00002 per 1K tokens (~$0.000003 per query)

---

#### Function: `rerank_documents_async(query, documents, top_n, config)`

**What it does**: Re-scores documents using deep semantic understanding

**Why reranking?**
- Vector similarity (cosine) is fast but shallow
- Cohere reranker understands context, intent, and nuance
- Dramatically improves result quality

**How it works:**
```python
co = cohere.ClientV2(api_key=config.cohere_api_key)
rerank_response = co.rerank(
    model="rerank-v3.5",
    query=query,
    documents=[doc['content'] for doc in documents],
    top_n=top_n
)
# Returns: documents with relevance_score (0.0-1.0)
```

**Performance**: ~0.7 seconds for 20 documents
**Cost**: ~$0.002 per 1K searches

---

#### Function: `search_documents_with_rerank(query, top_k, document_type, config)`

**What it does**: The complete search pipeline (see diagram above)

**Step-by-step:**

1. **Generate Query Embedding** (~1.5s)
   ```python
   query_embedding = await generate_embedding_async(query, config)
   ```

2. **Vector Search in Supabase** (~1.6s)
   ```python
   results = await asyncio.to_thread(
       lambda: supabase.rpc(config.match_function, {
           'query_embedding': query_embedding,
           'match_threshold': config.match_threshold,
           'match_count': min(top_k * 2, 100)
       }).execute()
   )
   ```
   - Uses `asyncio.to_thread()` because Supabase client is sync
   - Retrieves 2× requested results for better reranking

3. **Filter by Type** (optional)
   ```python
   if document_type:
       filtered = [r for r in results.data 
                   if r.get('metadata', {}).get('type') == document_type]
   ```

4. **Rerank with Cohere** (~0.7s)
   ```python
   reranked = await rerank_documents_async(
       query, filtered_results, top_k, config
   )
   ```

5. **Return Results**
   - Total time: ~5.7 seconds
   - Includes relevance scores, metadata, full content

**Error Handling:**
- Falls back to vector scores if Cohere fails
- Returns empty results with helpful message if no matches
- Standardized error format for all failures

---

#### Function: `browse_by_type(document_type, limit, offset, config)`

**What it does**: Retrieves documents filtered by type with pagination

**SQL Equivalent:**
```sql
SELECT id, content, metadata 
FROM n8n_law_startuplaw 
WHERE metadata->>'type' = 'agreement'
ORDER BY metadata->>'created_at' DESC
LIMIT 20 OFFSET 0;
```

**Returns:**
```json
{
  "document_type": "agreement",
  "page_size": 20,
  "offset": 0,
  "count": 15,
  "has_more": false,
  "documents": [...]
}
```

**Includes:**
- Document summaries (first 200 chars)
- Full metadata
- Pagination info

---

#### Function: `get_document(document_id, config)`

**What it does**: Retrieves complete document by UUID

**Validation:**
```python
try:
    uuid.UUID(document_id)  # Ensures valid UUID format
except ValueError:
    return error_response("Invalid UUID format")
```

**Returns:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Full document text...",
  "metadata": {...},
  "retrieved_at": "2025-12-10T12:00:00"
}
```

---

#### Function: `list_documents(limit, offset, include_content, config)`

**What it does**: Lists all documents with optional full content

**Key Feature: Content Toggle**
```python
fields = 'id, content, metadata' if include_content else 'id, metadata'
```

- `include_content=False`: Fast browsing with summaries
- `include_content=True`: Full content for each document

**Pagination Info:**
```json
{
  "total_documents": 347,
  "page_size": 50,
  "offset": 0,
  "current_page": 1,
  "total_pages": 7,
  "has_more": true,
  "documents": [...]
}
```

---

#### Utility Functions

**`retry_with_backoff()` and `async_retry_with_backoff()` decorators**

**What they do**: Automatically retry failed API calls

```python
@async_retry_with_backoff(max_retries=3, backoff_factor=2)
async def api_call():
    # If fails: Wait 1s, retry. Fail again: Wait 2s, retry. Fail again: Wait 4s, raise.
```

**Applied to:**
- OpenAI embedding generation
- Cohere reranking
- Prevents transient network failures from breaking the service

---

**`get_supabase_client()` with `@lru_cache`**

**What it does**: Reuses Supabase client across requests

```python
@lru_cache(maxsize=1)
def get_supabase_client(url: str, key: str) -> Client:
    logger.info("Creating new Supabase client")
    return create_client(url, key)
```

**Why cache?**
- ✅ Avoid creating new connections for each request
- ✅ Faster response times
- ✅ Reduced resource usage

---

**`create_error_response()`**

**What it does**: Standardizes all error messages

```json
{
  "error": true,
  "error_type": "validation_error",
  "message": "Query too long (max 1000 characters, got 1523)",
  "details": {},
  "timestamp": "2025-12-10T12:34:56.789"
}
```

**Error Types:**
- `validation_error`: Invalid input (UUID, query length, etc.)
- `search_error`: Search pipeline failure
- `browse_error`: Browse operation failure
- `retrieval_error`: Document fetch failure
- `list_error`: List operation failure
- `not_found`: Document doesn't exist

---

### 📄 `pyproject.toml` - Python Project Configuration

**Purpose**: Defines project metadata and dependencies

```toml
[project]
name = "mcp-server"
version = "0.1.0"
requires-python = ">=3.10,<3.14"

dependencies = [
    "mcp[cli]>=1.12.2",          # FastMCP framework
    "supabase>=2.10.0",           # Supabase client
    "openai>=1.57.4",             # OpenAI API client
    "cohere>=5.12.0",             # Cohere API client
    "python-dotenv>=1.1.1",       # .env file loader
    "uvicorn>=0.34.0",            # ASGI server for HTTP mode
    "numpy>=1.26.0",              # Array operations
]
```

**Why these dependencies?**
- `mcp[cli]`: Official MCP SDK with CLI tools
- `supabase`: Connect to Supabase database
- `openai`: Generate embeddings
- `cohere`: Rerank search results
- `python-dotenv`: Load environment variables
- `uvicorn`: Run HTTP server for remote deployment

**Python Version**: 3.10-3.13 (3.14 not supported yet - pydantic-core issues)

---

### 📄 `Dockerfile` - Containerization

**Purpose**: Packages the application for deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install UV package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application files
COPY legal_rag_server.py legal_rag_utils.py ./

# Set environment variables
ENV PORT=3000
ENV HOST=0.0.0.0

# Expose port
EXPOSE 3000

# Health check - verify port is listening
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', 3000)); s.close()" || exit 1

# Run server in HTTP mode
CMD ["uv", "run", "legal_rag_server.py", "--http"]
```

**Key Features:**
- ✅ Slim base image (smaller size, faster deployment)
- ✅ UV for fast dependency installation
- ✅ Layer caching (dependencies cached separately)
- ✅ Health check (Docker monitors server status)
- ✅ HTTP mode for remote access

---

### 📄 `.gitignore` - Git Ignore Rules

**Purpose**: Prevents sensitive and generated files from being committed

**Key Entries:**
```
__pycache__/          # Python bytecode
*.pyc, *.pyo         # Compiled Python files
.env                 # API KEYS - NEVER COMMIT!
*.log                # Log files
.venv/               # Virtual environment
dist/                # Build artifacts
.DS_Store            # macOS system files
```

**Critical**: `.env` file contains API keys and MUST be in `.gitignore`

---

## Data Flow Diagrams

### Flow 1: User Performs Semantic Search

```
┌────────────────────────────────────────────────────────────────┐
│                    USER ACTION IN CLAUDE                        │
└────────────────────────────────────────────────────────────────┘

User types: "Find SAFE agreement templates"
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│ Claude Desktop recognizes this as a search intent              │
│ Calls MCP tool: semantic_search_legal_documents()             │
│ Parameters:                                                     │
│   - query: "Find SAFE agreement templates"                     │
│   - top_k: 10                                                  │
│   - document_type: "agreement"                                 │
└──────────────────────────┬─────────────────────────────────────┘
                           │ MCP Protocol (stdio or HTTP)
                           ▼
┌────────────────────────────────────────────────────────────────┐
│              legal_rag_server.py receives request              │
│                                                                 │
│ 1. Validates inputs                                            │
│    ✓ Query not empty                                           │
│    ✓ Query length < 1000 chars                                 │
│    ✓ top_k between 1-100                                       │
│                                                                 │
│ 2. Calls: await search_documents_with_rerank(...)             │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│          legal_rag_utils.py: search_documents_with_rerank()    │
│                                                                 │
│ Step 1: Generate Embedding                                     │
│   → await generate_embedding_async(query, config)             │
│   → OpenAI API call                                            │
│   → Returns: [0.234, -0.567, 0.123, ...]                      │
│   ⏱ Time: ~1.5s                                                │
│                                                                 │
│ Step 2: Vector Search                                          │
│   → await asyncio.to_thread(supabase.rpc(...))                │
│   → Supabase compares with all document vectors               │
│   → Returns: Top 20 similar documents                          │
│   ⏱ Time: ~1.6s                                                │
│                                                                 │
│ Step 3: Filter by Type                                         │
│   → Filter where metadata.type == "agreement"                  │
│                                                                 │
│ Step 4: Rerank                                                 │
│   → await rerank_documents_async(...)                          │
│   → Cohere API deep semantic analysis                          │
│   → Returns: Top 10 with relevance scores                      │
│   ⏱ Time: ~0.7s                                                │
│                                                                 │
│ ⏱ Total Time: ~5.7 seconds                                     │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│              Results returned to legal_rag_server.py           │
│                                                                 │
│ {                                                               │
│   "query": "Find SAFE agreement templates",                    │
│   "document_type": "agreement",                                │
│   "total_results": 10,                                         │
│   "results": [                                                 │
│     {                                                           │
│       "id": "uuid-1",                                          │
│       "content": "SAFE Agreement template...",                 │
│       "metadata": {                                            │
│         "type": "agreement",                                   │
│         "title": "SAFE Agreement Template",                    │
│         "category": "Startup Financing"                        │
│       },                                                        │
│       "relevance_score": 0.94                                  │
│     },                                                          │
│     ...9 more results                                          │
│   ]                                                             │
│ }                                                               │
└──────────────────────────┬─────────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                    Claude Desktop receives results             │
│                                                                 │
│ Claude processes the results and presents to user:            │
│                                                                 │
│ "I found 10 SAFE agreement templates. The most relevant is:   │
│                                                                 │
│ 1. **SAFE Agreement Template** (Relevance: 94%)               │
│    This template covers post-money SAFE agreements for        │
│    early-stage startups. It includes standard terms for...    │
│                                                                 │
│ 2. **SAFE: Valuation Cap Template** (Relevance: 91%)          │
│    ...                                                          │
│                                                                 │
│ Would you like me to show you the full content of any of      │
│ these templates?"                                               │
└────────────────────────────────────────────────────────────────┘
```

---

### Flow 2: Error Handling

```
┌────────────────────────────────────────────────────────────────┐
│                    ERROR SCENARIOS                              │
└────────────────────────────────────────────────────────────────┘

Scenario 1: Invalid Input
───────────────────────────
User: Get document ID "not-a-uuid"
     │
     ▼
get_legal_document_by_id("not-a-uuid")
     │
     ▼
try:
    uuid.UUID("not-a-uuid")  # ❌ Raises ValueError
except ValueError:
    return create_error_response(
        error_type="validation_error",
        message="Invalid document ID format. Must be a valid UUID."
    )
     │
     ▼
Claude: "The document ID format is invalid. Please provide a valid 
         UUID in the format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"


Scenario 2: API Failure with Retry
───────────────────────────────────
generate_embedding_async("query")
     │
     ▼
@async_retry_with_backoff(max_retries=3)
async def generate_embedding_async(...):
    async with AsyncOpenAI() as client:
        response = await client.embeddings.create(...)  # ❌ Timeout
     │
     ▼
Attempt 1: Failed → Wait 1 second
Attempt 2: Failed → Wait 2 seconds  
Attempt 3: Success ✓
     │
     ▼
Return embedding


Scenario 3: Cohere Failure Fallback
────────────────────────────────────
try:
    reranked = await rerank_documents_async(...)  # ❌ Cohere API down
except Exception as e:
    logger.warning(f"Reranking failed: {e}. Falling back to vector scores.")
    reranked = filtered_results[:top_k]
    for doc in reranked:
        doc['relevance_score'] = doc.get('similarity', 0.0)
     │
     ▼
Return results with vector similarity scores instead
(Search still works, just slightly lower quality ranking)
```

---

## API Integration Flow

### OpenAI Integration

```
┌────────────────────────────────────────────────────────────────┐
│                    OPENAI EMBEDDING API                         │
└────────────────────────────────────────────────────────────────┘

Purpose: Convert text to 1536-dimensional semantic vectors

Request:
────────
POST https://api.openai.com/v1/embeddings
Headers:
  Authorization: Bearer sk-proj-...
  Content-Type: application/json
Body:
{
  "input": "How to structure a SAFE agreement?",
  "model": "text-embedding-3-small",
  "encoding_format": "float"
}

Response:
─────────
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [
        0.0023064255,
        -0.009327292,
        ...1532 more values...
        -0.0028842222
      ],
      "index": 0
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 8,
    "total_tokens": 8
  }
}

Cost: ~$0.00002 per 1K tokens
Typical query: ~$0.000003
```

---

### Cohere Integration

```
┌────────────────────────────────────────────────────────────────┐
│                    COHERE RERANK API                            │
└────────────────────────────────────────────────────────────────┘

Purpose: Re-score documents for semantic relevance

Request:
────────
POST https://api.cohere.ai/v1/rerank
Headers:
  Authorization: Bearer dOuDhVGel...
  Content-Type: application/json
Body:
{
  "model": "rerank-v3.5",
  "query": "How to structure a SAFE agreement?",
  "documents": [
    "SAFE Agreement template for startups...",
    "Series A financing guide...",
    "Employee stock options..."
  ],
  "top_n": 10
}

Response:
─────────
{
  "id": "rerank-abc123",
  "results": [
    {
      "index": 0,
      "relevance_score": 0.94587213
    },
    {
      "index": 2,
      "relevance_score": 0.23471829
    },
    {
      "index": 1,
      "relevance_score": 0.12093847
    }
  ],
  "meta": {
    "api_version": {
      "version": "2"
    }
  }
}

Cost: ~$0.002 per 1K searches
Typical search: ~$0.000002
```

---

### Supabase Integration

```
┌────────────────────────────────────────────────────────────────┐
│                    SUPABASE RPC FUNCTION                        │
└────────────────────────────────────────────────────────────────┘

Purpose: Vector similarity search in PostgreSQL with pgvector

PostgreSQL Function:
────────────────────
CREATE OR REPLACE FUNCTION match_n8n_law_startuplaw(
    query_embedding vector(1536),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id bigint,
    content text,
    metadata jsonb,
    embedding vector(1536),
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n8n_law_startuplaw.id,
        n8n_law_startuplaw.content,
        n8n_law_startuplaw.metadata,
        n8n_law_startuplaw.embedding,
        1 - (n8n_law_startuplaw.embedding <=> query_embedding) as similarity
    FROM n8n_law_startuplaw
    WHERE 1 - (n8n_law_startuplaw.embedding <=> query_embedding) > match_threshold
    ORDER BY n8n_law_startuplaw.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

Python Call:
────────────
results = supabase.rpc(
    'match_n8n_law_startuplaw',
    {
        'query_embedding': [0.234, -0.567, ...],  # 1536 floats
        'match_threshold': 0.5,                     # Minimum similarity
        'match_count': 20                           # Max results
    }
).execute()

Response:
─────────
{
  "data": [
    {
      "id": 1264,
      "content": "SAFE Agreement template...",
      "metadata": {
        "type": "agreement",
        "title": "SAFE Agreement",
        "category": "Startup Financing"
      },
      "embedding": [...1536 floats...],
      "similarity": 0.87234
    },
    ...19 more results
  ]
}

Vector Search Explanation:
──────────────────────────
• <=> is the "cosine distance" operator from pgvector
• Similarity = 1 - cosine_distance
• Higher similarity = more semantically similar
• Threshold 0.5 means 50% similarity or higher
• Index type: ivfflat or hnsw for fast approximate search
```

---

## Deployment Architecture

### Local Development (stdio mode)

```
┌────────────────────────────────────────────────────────────────┐
│                    LOCAL DEVELOPMENT                            │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│   Claude Desktop App    │
│   (Electron App)        │
│                         │
│  MCP Config:            │
│  {                      │
│    "command": "uv",     │
│    "args": [            │
│      "--directory",     │
│      "..path..",        │
│      "run",             │
│      "--python", "3.13",│
│      "legal_rag_        │
│      server.py"         │
│    ],                   │
│    "env": {             │
│      "SUPABASE_URL":    │
│      "...",             │
│      "OPENAI_API_KEY":  │
│      "..."              │
│    }                    │
│  }                      │
└────────┬────────────────┘
         │
         │ stdio (stdin/stdout)
         │
         ▼
┌────────────────────────────┐
│  Python Subprocess         │
│  legal_rag_server.py       │
│                            │
│  mcp.run()  # stdio mode   │
│                            │
│  • Reads from stdin        │
│  • Writes to stdout        │
│  • JSON-RPC protocol       │
└────────────────────────────┘
         │
         │ API Calls
         ▼
┌──────────────────────────────────────┐
│  External Services                    │
│  • Supabase (185.28.22.212:8000)    │
│  • OpenAI (api.openai.com)           │
│  • Cohere (api.cohere.ai)            │
└──────────────────────────────────────┘
```

---

### Production Deployment (HTTP mode on Coolify)

```
┌────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                        │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│   Claude Desktop App    │
│   (User's computer)     │
│                         │
│  MCP Config:            │
│  {                      │
│    "command": "npx",    │
│    "args": [            │
│      "@modelcontext     │
│      protocol/client",  │
│      "http://your-      │
│      domain.com:3000"   │
│    ]                    │
│  }                      │
└────────┬────────────────┘
         │
         │ HTTP/JSON-RPC
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│                    COOLIFY SERVER                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Nginx Reverse Proxy                                      │ │
│  │  • HTTPS termination                                      │ │
│  │  • Port forwarding: 443 → 3000                           │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                        │
│                       ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Docker Container                                         │ │
│  │                                                           │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  uvicorn server (0.0.0.0:3000)                     │  │ │
│  │  │                                                     │  │ │
│  │  │  app = mcp.streamable_http_app()                   │  │ │
│  │  │  uvicorn.run(app, host="0.0.0.0", port=3000)       │  │ │
│  │  │                                                     │  │ │
│  │  │  Endpoints:                                         │  │ │
│  │  │  • POST /mcp/v1/tools/call                         │  │ │
│  │  │  • GET  /health                                     │  │ │
│  │  │  • GET  /                                           │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                           │ │
│  │  Environment Variables:                                  │ │
│  │  • SUPABASE_URL=...                                      │ │
│  │  • OPENAI_API_KEY=...                                    │ │
│  │  • COHERE_API_KEY=...                                    │ │
│  │  • PORT=3000                                             │ │
│  │  • HOST=0.0.0.0                                          │ │
│  │                                                           │ │
│  │  Health Check:                                           │ │
│  │  • Checks port 3000 is listening every 30s              │ │
│  │  • Restart if 3 consecutive failures                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ API Calls
                         ▼
┌──────────────────────────────────────────────┐
│  External Services                            │
│  • Supabase (185.28.22.212:8000)            │
│  • OpenAI (api.openai.com)                   │
│  • Cohere (api.cohere.ai)                    │
└──────────────────────────────────────────────┘
```

---

## Performance Metrics

### Typical Request Timeline

```
┌────────────────────────────────────────────────────────────────┐
│          SEMANTIC SEARCH PERFORMANCE BREAKDOWN                  │
└────────────────────────────────────────────────────────────────┘

0.0s ─────────► Request received
              │
0.0s - 1.5s   │ OpenAI Embedding Generation
              │ • API call: 1.2s
              │ • Network: 0.3s
              │ ✓ Embedding: [1536 floats]
              │
1.5s - 3.1s   │ Supabase Vector Search
              │ • RPC call: 1.4s
              │ • Network: 0.2s
              │ ✓ Retrieved: 20 documents
              │
3.1s - 3.1s   │ Filter by Type (if specified)
              │ • In-memory filtering: <0.01s
              │ ✓ Filtered: 15 documents
              │
3.1s - 3.8s   │ Cohere Reranking
              │ • API call: 0.5s
              │ • Network: 0.2s
              │ ✓ Ranked: Top 10 documents
              │
3.8s ─────────► Response sent

Total: ~5.7 seconds ✓ (Target: 7-11 seconds)

Cost per search:
• OpenAI:  $0.000003
• Cohere:  $0.000002
• Supabase: Free (self-hosted)
────────────────────
Total:     $0.000005 per search
```

### Optimization Opportunities

```
Current vs Optimized:
─────────────────────

CURRENT APPROACH (Sequential):
OpenAI (1.5s) → Supabase (1.6s) → Cohere (0.7s) = 5.7s

POTENTIAL OPTIMIZATIONS:

1. Embedding Cache (90% cache hit rate):
   ┌────────────────────────────────────────┐
   │ Check cache → Hit!                     │
   │ Time: 0.001s instead of 1.5s           │
   │ Savings: ~1.5s per cached query        │
   │ Implementation: @lru_cache or Redis    │
   └────────────────────────────────────────┘
   New total: ~4.2 seconds (-27%)

2. Connection Pooling (already implemented ✓):
   ┌────────────────────────────────────────┐
   │ Reuse Supabase client connections      │
   │ Savings: ~0.1-0.2s per request         │
   │ Status: ✓ Implemented with @lru_cache  │
   └────────────────────────────────────────┘

3. Batch Queries (future enhancement):
   ┌────────────────────────────────────────┐
   │ Process multiple queries in parallel   │
   │ Use: asyncio.gather()                  │
   │ Benefit: 2x-3x throughput              │
   └────────────────────────────────────────┘
```

---

## Security Considerations

### API Key Management

```
┌────────────────────────────────────────────────────────────────┐
│                    API KEY SECURITY                             │
└────────────────────────────────────────────────────────────────┘

✓ GOOD PRACTICES (Currently Implemented):
──────────────────────────────────────────
1. Environment Variables
   • Stored in .env file
   • Never committed to git (.gitignore)
   • Loaded with python-dotenv

2. Service Role Key Usage
   • Using Supabase service role key
   • Full permissions (backend only)
   • Not exposed to client

3. HTTPS for All API Calls
   • OpenAI: https://api.openai.com
   • Cohere: https://api.cohere.ai
   • Supabase: Can use HTTPS

❌ RISKS TO BE AWARE OF:
────────────────────────
1. Claude Desktop Config
   • API keys visible in config file
   • Config stored at: C:\Users\...\Claude\claude_desktop_config.json
   • ⚠️ Backed up to OneDrive/cloud storage
   • Mitigation: Document security best practices

2. Plaintext Logs
   • API keys might appear in logs if not careful
   • Current: Keys not logged ✓
   • Recommendation: Implement log sanitization

3. No Rate Limiting
   • Unlimited API calls possible
   • Could lead to unexpected costs
   • Recommendation: Implement per-user rate limits
```

### Recommended Security Enhancements

```python
# 1. API Key Rotation
# Regularly rotate keys and update .env

# 2. Request Rate Limiting
from functools import wraps
import time

def rate_limit(max_per_minute=60):
    """Limit to 60 requests per minute"""
    # Implementation here

# 3. Input Sanitization (already implemented ✓)
def validate_query(query: str) -> bool:
    if len(query) > 1000:
        raise ValueError("Query too long")
    # Prevent SQL injection, XSS, etc.

# 4. Audit Logging
logger.info(f"User query: {query[:50]}...")  # Log first 50 chars
logger.info(f"Results returned: {len(results)}")
logger.info(f"API costs: ${total_cost:.6f}")
```

---

## Troubleshooting Guide

### Common Issues and Solutions

```
┌────────────────────────────────────────────────────────────────┐
│                    TROUBLESHOOTING                              │
└────────────────────────────────────────────────────────────────┘

Issue 1: "Missing required environment variables"
────────────────────────────────────────────────
Symptom: Server fails to start
Cause: .env file missing or incomplete
Solution:
  1. Check .env file exists in MCP_Server/
  2. Verify all 4 keys are present:
     - SUPABASE_URL
     - SUPABASE_SERVICE_ROLE_KEY
     - OPENAI_API_KEY
     - COHERE_API_KEY
  3. Remove quotes around values
  4. Restart Claude Desktop


Issue 2: "No results received from client-side tool execution"
────────────────────────────────────────────────────────────────
Symptom: Tool calls fail silently in Claude Desktop
Cause: Server crashed during initialization
Solution:
  1. Check server log: legal_rag_server.log
  2. Look for errors at startup
  3. Verify environment variables in Claude config
  4. Test server manually: python legal_rag_server.py


Issue 3: Requests timeout after 240 seconds
────────────────────────────────────────────
Symptom: Search takes 4 minutes then fails
Cause: AsyncOpenAI client not properly closed
Solution: ✓ FIXED - Using async with context manager
  Old: client = AsyncOpenAI(); response = await client.embeddings.create()
  New: async with AsyncOpenAI() as client: response = await client.embeddings.create()


Issue 4: "404 Not Found" from Supabase
───────────────────────────────────────
Symptom: Vector search fails
Cause: RPC function signature mismatch
Solution:
  1. Verify function exists in Supabase
  2. Check parameter types match:
     - query_embedding: vector(1536)
     - match_threshold: FLOAT
     - match_count: INT
  3. Test with curl: curl -X POST http://supabase/rest/v1/rpc/match_...


Issue 5: High API costs
───────────────────────
Symptom: Unexpected OpenAI/Cohere bills
Cause: Too many searches or large queries
Solution:
  1. Implement embedding cache (@lru_cache or Redis)
  2. Add rate limiting per user
  3. Monitor usage in API dashboards
  4. Set billing alerts


Issue 6: Slow search performance
─────────────────────────────────
Symptom: Searches take > 10 seconds
Cause: Multiple possible causes
Solution:
  1. Check each stage timing in logs
  2. Optimize slow stage:
     - OpenAI: Use smaller model or cache
     - Supabase: Check indexing (ivfflat/hnsw)
     - Cohere: Reduce document count
  3. Ensure async operations don't block


Issue 7: Docker container won't start
──────────────────────────────────────
Symptom: Container restarts continuously
Cause: Health check fails or startup error
Solution:
  1. Check logs: docker logs <container_id>
  2. Verify environment variables passed to container
  3. Test health check: docker exec <container> python -c "import socket..."
  4. Increase health check start-period in Dockerfile
```

---

## Summary

### Key Takeaways

**Architecture:**
- 🏗️ **Modular Design**: Server layer (MCP) + Business logic (utils) + External services
- 🔌 **Flexible Deployment**: Local (stdio) or Remote (HTTP)
- 🎯 **Focused Tools**: 4 well-defined MCP tools for legal document retrieval

**Technology:**
- 🤖 **AI-Powered**: OpenAI embeddings + Cohere reranking = high-quality results
- 📊 **Vector Database**: Supabase pgvector for fast similarity search
- ⚡ **Async Architecture**: Non-blocking I/O for better performance

**Performance:**
- ⏱️ **Fast**: ~5.7 seconds per search (better than 7-11s target)
- 💰 **Cost-Effective**: ~$0.000005 per search
- 🔄 **Reliable**: Retry logic + fallback mechanisms

**Security:**
- 🔐 **Environment Variables**: API keys in .env (gitignored)
- 🛡️ **Input Validation**: Query length, UUID format, parameter ranges
- 📝 **Error Handling**: Comprehensive error messages without exposing internals

---

## Next Steps

**For Development:**
1. ✅ All core features implemented
2. ✅ Testing suite complete
3. ✅ Documentation comprehensive
4. 🔄 Consider adding embedding cache for production
5. 🔄 Implement rate limiting if multi-user

**For Production:**
1. ✅ Docker deployment ready
2. ✅ Health checks configured
3. ✅ Environment variables documented
4. 🔄 Set up monitoring (API costs, request counts)
5. 🔄 Regular API key rotation

**For Users:**
1. ✅ Claude Desktop integration working
2. ✅ All 4 tools accessible
3. ✅ Search returning quality results
4. 📚 Read README_LEGAL_RAG.md for usage examples
5. 🔧 Check TESTING_GUIDE.md for testing procedures

---

## File Dependency Map

```
project_root/
│
├── MCP_Server/
│   ├── legal_rag_server.py        ← Entry point (imports legal_rag_utils)
│   │   └─ depends on ──────────┐
│   │                            │
│   ├── legal_rag_utils.py      ←┘ Core business logic
│   │   └─ uses ───────────────────► External APIs (OpenAI, Cohere, Supabase)
│   │
│   ├── pyproject.toml             ← Dependencies definition
│   ├── uv.lock                     ← Locked versions
│   ├── .env                        ← API keys (gitignored)
│   ├── .gitignore                  ← Prevents committing secrets
│   │
│   ├── Dockerfile                  ← Container definition
│   │   └─ uses ──────────────────► pyproject.toml, legal_rag_*.py
│   │
│   ├── test/
│   │   ├── test_legal_rag.py      ← Test suite
│   │   └── TESTING_GUIDE.md       ← Testing instructions
│   │
│   ├── specs/
│   │   └── legal-rag-server/
│   │       ├── requirements.md     ← Business requirements
│   │       └── implementation-plan.md ← Technical plan
│   │
│   └── DEPLOYMENT_GUIDE.md         ← Deployment instructions
│
└── Claude Desktop Config:
    C:\Users\joong\AppData\Roaming\Claude\claude_desktop_config.json
    └─ launches ──────────────────► legal_rag_server.py
```

---

**End of Architecture Guide**

For more information:
- [README_LEGAL_RAG.md](./README_LEGAL_RAG.md) - User guide
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment instructions
- [TESTING_GUIDE.md](./test/TESTING_GUIDE.md) - Testing procedures
- [requirements.md](./specs/legal-rag-server/requirements.md) - Requirements
- [implementation-plan.md](./specs/legal-rag-server/implementation-plan.md) - Implementation details

