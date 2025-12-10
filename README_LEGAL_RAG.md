# Legal Document RAG MCP Server

A Model Context Protocol (MCP) server that provides AI-powered semantic search and document retrieval for legal documents stored in Supabase. Built with FastMCP, OpenAI embeddings, and Cohere reranking.

## Features

- **Semantic Search**: Natural language queries with vector similarity search
- **AI-Powered Reranking**: Cohere rerank-v3.5 for optimal result ordering
- **Type Filtering**: Filter by document type (agreements, clauses, practice guides)
- **Pagination**: Efficient browsing of large document collections
- **Error Handling**: Comprehensive error handling with automatic retries
- **Performance Optimized**: Async operations, connection pooling, and caching

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Desktop                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP Protocol
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              legal_rag_server.py (FastMCP)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool 1: semantic_search_legal_documents             │  │
│  │  Tool 2: browse_legal_documents_by_type              │  │
│  │  Tool 3: get_legal_document_by_id                    │  │
│  │  Tool 4: list_all_legal_documents                    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              legal_rag_utils.py (Business Logic)             │
│  • OpenAI Embeddings (text-embedding-3-small)               │
│  • Cohere Reranking (rerank-v3.5)                           │
│  • Supabase Vector Search                                   │
│  • Error Handling & Retry Logic                             │
└──────────┬─────────────┬──────────────┬────────────────────┘
           │             │              │
           ▼             ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌───────────┐
    │ Supabase │  │  OpenAI  │  │  Cohere   │
    │ Database │  │   API    │  │   API     │
    └──────────┘  └──────────┘  └───────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- UV package manager (or pip)
- Claude Desktop installed
- API keys for:
  - Supabase (with vector search enabled)
  - OpenAI
  - Cohere

### Step 1: Install Dependencies

```bash
cd MCP_Server
uv sync  # or pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the `MCP_Server` directory:

```env
# Required API Keys
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
OPENAI_API_KEY=your_openai_api_key_here
COHERE_API_KEY=your_cohere_api_key_here

# Optional Configuration (with defaults)
LEGAL_RAG_TABLE_NAME=n8n_law_startuplaw
LEGAL_RAG_MATCH_FUNCTION=match_n8n_law_startuplaw
LEGAL_RAG_TOP_K=10
LEGAL_RAG_MATCH_THRESHOLD=0.5
```

**⚠️ Security Note**: Never commit the `.env` file to version control. It contains sensitive API keys.

### Step 3: Set Up Supabase Vector Search

Your Supabase database needs a vector search function. Here's an example:

```sql
CREATE OR REPLACE FUNCTION match_n8n_law_startuplaw(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n8n_law_startuplaw.id,
        n8n_law_startuplaw.content,
        n8n_law_startuplaw.metadata,
        1 - (n8n_law_startuplaw.embedding <=> query_embedding) as similarity
    FROM n8n_law_startuplaw
    WHERE 1 - (n8n_law_startuplaw.embedding <=> query_embedding) > match_threshold
    ORDER BY n8n_law_startuplaw.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Step 4: Install to Claude Desktop

```bash
# Using UV
uv run mcp install legal_rag_server.py

# Or manually add to Claude Desktop config
# Location: %APPDATA%\Claude\claude_desktop_config.json (Windows)
# Location: ~/Library/Application Support/Claude/claude_desktop_config.json (Mac)
```

Manual configuration:

```json
{
  "mcpServers": {
    "legal-rag": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\MCP_Server",
        "run",
        "legal_rag_server.py"
      ]
    }
  }
}
```

### Step 5: Restart Claude Desktop

Close and reopen Claude Desktop. The legal RAG tools should now be available.

## Available Tools

### 1. semantic_search_legal_documents

Search legal documents using natural language queries with AI-powered semantic search.

**Parameters:**
- `query` (string, required): Natural language search query
- `top_k` (integer, default: 10): Number of results to return (1-100)
- `document_type` (string, optional): Filter by type - "practice_guide", "agreement", or "clause"

**Example Queries:**
```
"SAFE agreement best practices"
"incorporation checklist for Delaware C-corp"
"employee stock option plan template"
```

**Response:**
```json
{
  "query": "SAFE agreement",
  "document_type": null,
  "total_results": 5,
  "results": [
    {
      "id": "uuid-here",
      "content": "Full document content...",
      "metadata": {
        "type": "agreement",
        "title": "SAFE Agreement Guide"
      },
      "relevance_score": 0.95
    }
  ]
}
```

### 2. browse_legal_documents_by_type

Browse documents filtered by type with pagination.

**Parameters:**
- `document_type` (string, required): "practice_guide", "agreement", or "clause"
- `limit` (integer, default: 20): Documents per page (1-100)
- `offset` (integer, default: 0): Pagination offset

**Example:**
```
Browse all agreement templates
Get next page: offset=20
```

**Response:**
```json
{
  "document_type": "agreement",
  "page_size": 20,
  "offset": 0,
  "count": 15,
  "has_more": false,
  "documents": [
    {
      "id": "uuid-here",
      "type": "agreement",
      "title": "SAFE Agreement",
      "summary": "First 200 characters...",
      "metadata": {...}
    }
  ]
}
```

### 3. get_legal_document_by_id

Retrieve a specific document by its UUID.

**Parameters:**
- `document_id` (string, required): UUID of the document

**Example:**
```
document_id="550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Full document content here...",
  "metadata": {
    "type": "agreement",
    "title": "Document Title",
    "created_at": "2024-01-15"
  },
  "retrieved_at": "2024-01-20T10:30:00"
}
```

### 4. list_all_legal_documents

List all documents with pagination.

**Parameters:**
- `limit` (integer, default: 50): Documents per page (1-100)
- `offset` (integer, default: 0): Pagination offset
- `include_content` (boolean, default: false): Include full content or just summaries

**Example:**
```
First page with summaries: limit=50, offset=0, include_content=false
Second page with full content: limit=50, offset=50, include_content=true
```

**Response:**
```json
{
  "total_documents": 150,
  "page_size": 50,
  "offset": 0,
  "current_page": 1,
  "total_pages": 3,
  "has_more": true,
  "documents": [...]
}
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | (required) | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | (required) | Service role key (not anon key) |
| `OPENAI_API_KEY` | (required) | OpenAI API key for embeddings |
| `COHERE_API_KEY` | (required) | Cohere API key for reranking |
| `LEGAL_RAG_TABLE_NAME` | `n8n_law_startuplaw` | Supabase table name |
| `LEGAL_RAG_MATCH_FUNCTION` | `match_n8n_law_startuplaw` | Vector search function name |
| `LEGAL_RAG_TOP_K` | `10` | Default number of results |
| `LEGAL_RAG_MATCH_THRESHOLD` | `0.5` | Minimum similarity threshold (0.0-1.0) |

### Tuning Match Threshold

The `match_threshold` controls how similar documents must be to appear in results:

- **0.3-0.5**: More results, lower precision (good for exploration)
- **0.5-0.7**: Balanced (recommended default)
- **0.7-0.9**: Fewer results, higher precision (strict matching)

## Usage Examples

### In Claude Desktop

Once installed, you can ask Claude to use these tools naturally:

**Example 1: Search**
```
User: "Find documents about SAFE agreements"
Claude: [Uses semantic_search_legal_documents tool]
```

**Example 2: Browse by Type**
```
User: "Show me all practice guides"
Claude: [Uses browse_legal_documents_by_type with document_type="practice_guide"]
```

**Example 3: Get Specific Document**
```
User: "Get the document with ID 550e8400-e29b-41d4-a716-446655440000"
Claude: [Uses get_legal_document_by_id tool]
```

**Example 4: List All**
```
User: "List all legal documents in the database"
Claude: [Uses list_all_legal_documents tool]
```

## Testing

### Run Unit Tests

```bash
# Install test dependencies
uv add --dev pytest pytest-asyncio pytest-mock

# Run all tests
pytest test_legal_rag.py -v

# Run specific test class
pytest test_legal_rag.py::TestSearchDocuments -v

# Run with coverage
pytest test_legal_rag.py --cov=legal_rag_utils --cov-report=html
```

### Test in MCP Dev Mode

```bash
# Start MCP inspector
uv run mcp dev legal_rag_server.py

# Test tools in browser interface at http://localhost:5173
```

### Manual Integration Test

```python
import asyncio
from legal_rag_utils import LegalRAGConfig, search_documents_with_rerank

async def test_search():
    config = LegalRAGConfig.from_env()
    result = await search_documents_with_rerank(
        query="SAFE agreement",
        top_k=5,
        document_type=None,
        config=config
    )
    print(result)

asyncio.run(test_search())
```

## Troubleshooting

### Issue: "Missing required environment variables"

**Solution**:
- Check that your `.env` file exists in the `MCP_Server` directory
- Verify all 4 required API keys are set
- Ensure there are no quotes around the values

### Issue: "Supabase connection failed"

**Solution**:
- Verify `SUPABASE_URL` starts with `https://` or `http://`
- Check that you're using the service role key, not the anon key
- Test network connectivity to Supabase

### Issue: "OpenAI rate limit exceeded"

**Solution**:
- Wait a few minutes and retry
- Consider implementing a rate limiter
- Upgrade your OpenAI API tier

### Issue: "No results found"

**Solution**:
- Check if documents exist in your Supabase table
- Verify the table name matches `LEGAL_RAG_TABLE_NAME`
- Try lowering `LEGAL_RAG_MATCH_THRESHOLD` (e.g., 0.3)
- Ensure your query is relevant to the document content

### Issue: "Cohere reranking failed"

**Solution**: The system automatically falls back to vector similarity scores. Check your Cohere API key and quota.

### Issue: "Tools not showing in Claude Desktop"

**Solution**:
1. Verify the MCP server is in `claude_desktop_config.json`
2. Check the file path is correct
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### Viewing Logs

Logs are written to:
- Console output (stdout)
- `legal_rag_server.log` file in the `MCP_Server` directory

To adjust log level, edit `legal_rag_utils.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more details
    ...
)
```

## Performance Optimization

### Current Optimizations

1. **Supabase Client Caching**: Single client instance reused across requests
2. **Async Operations**: Non-blocking I/O for all external API calls
3. **Connection Pooling**: Efficient database connection management
4. **Automatic Retries**: Exponential backoff for transient failures

### Future Optimizations (Optional)

1. **Embedding Cache**: Cache embeddings for common queries
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def cached_generate_embedding(query: str, model: str) -> List[float]:
       # Implementation
   ```

2. **Parallel Operations**: Run independent operations concurrently
   ```python
   results = await asyncio.gather(
       generate_embedding_async(query1, config),
       generate_embedding_async(query2, config)
   )
   ```

3. **Redis Caching**: Distributed cache for multi-instance deployments

## API Costs

Approximate costs per request:

| Service | Operation | Cost |
|---------|-----------|------|
| OpenAI | Embedding generation | ~$0.00002 per query |
| Cohere | Reranking 20 docs | ~$0.00004 per query |
| Supabase | Vector search | Included in plan |

**Estimated total**: ~$0.00006 per semantic search query

## Security Best Practices

1. **Never commit `.env` file**: Add to `.gitignore`
2. **Use service role key**: Not the anon key for Supabase
3. **Rotate API keys regularly**: Update in `.env` and restart
4. **Limit API key permissions**: Use least privilege principle
5. **Monitor API usage**: Set up alerts for unusual activity

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions under 50 lines when possible

### Adding New Features

1. Add business logic to `legal_rag_utils.py`
2. Add MCP tool to `legal_rag_server.py`
3. Add tests to `test_legal_rag.py`
4. Update this README

### Running Pre-commit Checks

```bash
# Format code
black legal_rag_utils.py legal_rag_server.py

# Type checking
mypy legal_rag_utils.py legal_rag_server.py

# Linting
ruff check legal_rag_utils.py legal_rag_server.py
```

## License

[Your License Here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the implementation plan: `specs/legal-rag-server/implementation-plan.md`
- Check logs in `legal_rag_server.log`

## Changelog

### Version 1.0.0 (2025-12-10)

- Initial release
- 4 MCP tools for legal document search and retrieval
- OpenAI embeddings and Cohere reranking
- Comprehensive error handling and logging
- Full async/await support
- Client caching and performance optimizations
- Complete test suite
- Documentation
