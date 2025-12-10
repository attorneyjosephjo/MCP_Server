# Legal Document RAG MCP Server

A Model Context Protocol (MCP) server that provides semantic search and retrieval for legal documents stored in Supabase. This server integrates with Claude Desktop to enable natural language queries over legal documents using vector embeddings and AI-powered reranking.

## Features

- **Semantic Search**: Search legal documents using natural language queries with OpenAI embeddings
- **AI-Powered Reranking**: Results reranked using Cohere's rerank-v3.5 model for improved relevance
- **Document Browsing**: Filter and browse documents by type (practice guides, agreements, clauses)
- **Direct Document Retrieval**: Fetch specific documents by UUID
- **Paginated Listing**: List all documents with pagination support
- **Error Handling**: Robust error handling with automatic retry logic and fallback strategies

## Architecture

```
┌─────────────────────────────────────────┐
│         Claude Desktop                  │
└──────────────┬──────────────────────────┘
               │ MCP Protocol
               ▼
┌─────────────────────────────────────────┐
│     legal_rag_server.py (FastMCP)       │
│  ┌────────────────────────────────────┐ │
│  │  4 Tools:                          │ │
│  │  • semantic_search_legal_documents │ │
│  │  • browse_legal_documents_by_type  │ │
│  │  • get_legal_document_by_id        │ │
│  │  • list_all_legal_documents        │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   legal_rag_utils.py (Business Logic)   │
│  • Configuration Management             │
│  • OpenAI Embeddings (1536-dim)        │
│  • Cohere Reranking                    │
│  • Supabase Vector Search              │
└──────┬──────────┬──────────┬───────────┘
       │          │          │
       ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐
  │Supabase│ │ OpenAI │ │ Cohere │
  └────────┘ └────────┘ └────────┘
```

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/) package manager
- [Claude Desktop](https://claude.ai/download)
- Supabase account with vector search configured
- OpenAI API key
- Cohere API key

## Installation

### 1. Install UV Package Manager

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**MacOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

More info: https://docs.astral.sh/uv/getting-started/installation/

### 2. Download Claude Desktop

Download Claude Desktop from: https://claude.ai/download

### 3. Clone/Navigate to the Project

```bash
cd MCP_Server
```

### 4. Install Dependencies

```bash
uv sync
```

This will install all required packages:
- `mcp` - Model Context Protocol SDK
- `fastmcp` - FastMCP framework
- `supabase` - Supabase client
- `openai` - OpenAI API client
- `cohere` - Cohere API client
- `python-dotenv` - Environment variable management

## Configuration

### 1. Set Up Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Configure Your API Keys

Edit `.env` and add your credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Cohere Configuration
COHERE_API_KEY=your-cohere-api-key-here

# Optional: Customize table and function names
LEGAL_RAG_TABLE_NAME=n8n_law_startuplaw
LEGAL_RAG_MATCH_FUNCTION=match_n8n_law_startuplaw
LEGAL_RAG_TOP_K=10
```

### 3. Supabase Setup Requirements

Your Supabase database must have:

**Table Structure:**
```sql
CREATE TABLE n8n_law_startuplaw (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536)
);
```

**Vector Search Function:**
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
        1 - (n8n_law_startuplaw.embedding <=> query_embedding) AS similarity
    FROM n8n_law_startuplaw
    WHERE 1 - (n8n_law_startuplaw.embedding <=> query_embedding) > match_threshold
    ORDER BY n8n_law_startuplaw.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

## Usage

### Testing with MCP Dev Mode

Before installing to Claude Desktop, test the server:

```bash
uv run mcp dev legal_rag_server.py
```

This opens the MCP inspector in your browser where you can:
- View all 4 available tools
- Test each tool with sample inputs
- Verify API connections
- Debug any configuration issues

### Install to Claude Desktop

```bash
uv run mcp install legal_rag_server.py
```

### Restart Claude Desktop

1. Close Claude Desktop completely
2. Reopen the application
3. Wait for it to fully load
4. The 4 legal document tools should now be available

## Available Tools

### 1. semantic_search_legal_documents

Search legal documents using natural language queries.

**Parameters:**
- `query` (str): Natural language search query
- `top_k` (int, optional): Number of results to return (default: 10, max: 100)
- `document_type` (str, optional): Filter by type - "practice_guide", "agreement", or "clause"

**Example queries:**
```
"Search for SAFE agreement templates"
"Find clauses about intellectual property"
"Show practice guides on startup financing"
```

### 2. browse_legal_documents_by_type

Browse documents filtered by type with pagination.

**Parameters:**
- `document_type` (str): Type of document - "practice_guide", "agreement", or "clause"
- `limit` (int, optional): Documents per page (default: 20, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)

**Example queries:**
```
"Show me all practice guides"
"Browse agreement documents, page 2"
"List all clauses"
```

### 3. get_legal_document_by_id

Retrieve a specific legal document by its UUID.

**Parameters:**
- `document_id` (str): UUID of the document

**Example queries:**
```
"Get document 123e4567-e89b-12d3-a456-426614174000"
"Show me the full content of document [UUID]"
```

### 4. list_all_legal_documents

List all legal documents with pagination.

**Parameters:**
- `limit` (int, optional): Documents per page (default: 50, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)
- `include_content` (bool, optional): Include full content (default: false)

**Example queries:**
```
"List all legal documents"
"Show me page 3 of all documents"
"List documents with full content"
```

## Project Structure

```
MCP_Server/
├── legal_rag_server.py          # Main MCP server with FastMCP tools
├── legal_rag_utils.py           # Core business logic and API integrations
├── specs/
│   └── legal-rag-server/
│       ├── requirements.md      # Feature requirements
│       └── implementation-plan.md  # Detailed implementation plan
├── pyproject.toml               # Project dependencies
├── .env.example                 # Environment variable template
├── .env                         # Your actual API keys (gitignored)
├── uv.lock                      # Dependency lock file
└── README.md                    # This file
```

## How It Works

### 1. Semantic Search Flow

1. User asks a natural language question in Claude Desktop
2. Query is sent to `semantic_search_legal_documents` tool
3. OpenAI generates a 1536-dimensional embedding of the query
4. Supabase performs vector similarity search
5. Top results (2x requested) are retrieved
6. Cohere reranks results for improved relevance
7. Top-k most relevant documents are returned

### 2. Vector Embeddings

- Model: `text-embedding-3-small`
- Dimensions: 1536
- Provider: OpenAI
- Cost: ~$0.00002 per 1K tokens

### 3. Reranking

- Model: `rerank-v3.5`
- Provider: Cohere
- Fallback: If reranking fails, uses vector similarity scores
- Cost: ~$0.002 per 1K searches

## Error Handling

The server includes robust error handling:

- **Automatic Retry**: API calls retry 3 times with exponential backoff (1s, 2s, 4s)
- **Graceful Fallback**: If Cohere reranking fails, falls back to vector similarity scores
- **Validation**: Input validation for document types, UUIDs, pagination parameters
- **Clear Messages**: Helpful error messages for debugging

## Testing

### Manual Testing Checklist

- [ ] Configuration loads from .env correctly
- [ ] Semantic search returns relevant results
- [ ] Document type filtering works
- [ ] Browse by type returns correct documents
- [ ] Get by ID retrieves specific documents
- [ ] Pagination works correctly
- [ ] Error messages are clear and helpful

### Test Queries for Claude Desktop

```
"Search for SAFE agreement templates"
"Show me all practice guides"
"List the first 10 legal documents"
"What documents do you have about intellectual property?"
"Browse all agreements"
```

## Troubleshooting

### Common Issues

**"Missing required environment variables"**
- Verify all 4 API keys are set in `.env`
- Check for typos in variable names

**"Supabase connection failed"**
- Verify `SUPABASE_URL` starts with `https://`
- Ensure you're using the service role key, not the anon key
- Test network connectivity to Supabase

**"No results found"**
- Check that documents exist in your Supabase table
- Verify the table name matches your configuration
- Try adjusting the match_threshold in the code (default: 0.5)

**"OpenAI rate limit exceeded"**
- Wait and retry
- Consider upgrading your OpenAI API tier
- Implement rate limiting in your application

**"uv command not found"**
- Install UV using the installation commands above
- Add UV to your system PATH

### Enable Debug Logging

Add to `legal_rag_utils.py`:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('legal_rag')
```

## API Costs (Approximate)

- OpenAI Embeddings: $0.00002 per 1K tokens (~$0.0001 per query)
- Cohere Reranking: $0.002 per 1K searches (~$0.000002 per query)
- Supabase: Included in free tier for moderate usage

**Example:** 1,000 searches/month ≈ $0.20

## Further Reading

- [Model Context Protocol Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Supabase Vector Guide](https://supabase.com/docs/guides/ai/vector-indexes)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Reranking](https://docs.cohere.com/docs/reranking)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the implementation plan in `specs/legal-rag-server/`
- Open an issue on GitHub
