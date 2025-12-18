from dotenv import load_dotenv
import logging
import os
from mcp.server.fastmcp import FastMCP
from legal_rag_utils import (
    LegalRAGConfig,
    search_documents_with_rerank,
    browse_by_type,
    get_document,
    list_documents,
    create_error_response,
    get_cached_supabase_client
)

load_dotenv()

# Get logger from legal_rag_utils
logger = logging.getLogger('legal_rag')

# Initialize MCP server
mcp = FastMCP("LegalDocumentRAGServer")

# Load configuration
try:
    config = LegalRAGConfig.from_env()
    config.validate()
    logger.info("Legal RAG Server configuration loaded successfully")
except Exception as e:
    logger.error(f"Configuration error: {e}")
    logger.error("Please ensure all required environment variables are set in .env file")
    raise


@mcp.tool()
async def semantic_search_legal_documents(
    query: str,
    top_k: int = 10,
    document_type: str = None
) -> dict:
    """
    Search legal documents using natural language queries with AI-powered semantic search.

    This tool uses OpenAI embeddings for vector similarity search and Cohere reranking
    to find the most relevant legal documents matching your query.

    Args:
        query: Natural language search query (e.g., "How to structure a SAFE agreement?")
        top_k: Number of results requested (default: 10, max: 10)
               Note: System returns up to 5 documents to optimize for Claude's context window.
               If you request 10, you'll receive the top 5 most relevant results.
        document_type: Optional filter - "practice_notes_checklists", "standard_documents_clauses", "cases", or "laws_regulations"

    Returns:
        Dictionary with search results, each containing document content, metadata, and relevance score

    Examples:
        - "SAFE agreement best practices"
        - "incorporation checklist for Delaware C-corp"
        - "employee stock option plan template"
    """
    try:
        # Validate query length
        if not query or len(query.strip()) == 0:
            return create_error_response(
                error_type="validation_error",
                message="Query cannot be empty"
            )

        if len(query) > 1000:
            return create_error_response(
                error_type="validation_error",
                message=f"Query too long (max 1000 characters, got {len(query)})"
            )

        # Validate top_k
        if top_k < 1 or top_k > 10:
            return create_error_response(
                error_type="validation_error",
                message="top_k must be between 1 and 10"
            )

        return await search_documents_with_rerank(
            query=query,
            top_k=top_k,
            document_type=document_type,
            config=config
        )
    except Exception as e:
        return create_error_response(
            error_type="search_error",
            message=f"Search failed: {str(e)}"
        )


@mcp.tool()
def browse_legal_documents_by_type(
    document_type: str,
    limit: int = 20,
    offset: int = 0
) -> dict:
    """
    Browse legal documents filtered by type with pagination.

    Retrieve documents organized by category to explore specific types of legal content.

    Args:
        document_type: Type of document - "practice_notes_checklists", "standard_documents_clauses", "cases", or "laws_regulations"
        limit: Number of documents per page (default: 20, max: 100)
        offset: Pagination offset (default: 0)

    Returns:
        Dictionary with paginated documents and metadata

    Document Types:
        - practice_notes_checklists: Practice notes and checklists
        - standard_documents_clauses: Standard documents and clauses
        - cases: Case law
        - laws_regulations: Laws and regulations

    Examples:
        - Browse all standard documents: document_type="standard_documents_clauses"
        - Get next page of practice notes: document_type="practice_notes_checklists", offset=20
    """
    try:
        return browse_by_type(
            document_type=document_type,
            limit=limit,
            offset=offset,
            config=config
        )
    except Exception as e:
        return create_error_response(
            error_type="browse_error",
            message=f"Browse failed: {str(e)}"
        )


@mcp.tool()
def get_legal_document_by_id(document_id: str) -> dict:
    """
    Retrieve a specific legal document by its unique ID.

    Use this tool when you have a document ID from a previous search or list operation
    and want to retrieve the full document content.

    Args:
        document_id: Unique ID of the document (integer string, e.g. "123")

    Returns:
        Complete document with full content and metadata

    Example:
        document_id="12345"
    """
    try:
        return get_document(
            document_id=document_id,
            config=config
        )
    except Exception as e:
        return create_error_response(
            error_type="retrieval_error",
            message=f"Document retrieval failed: {str(e)}"
        )


@mcp.tool()
def list_all_legal_documents(
    limit: int = 50,
    offset: int = 0,
    include_content: bool = False
) -> dict:
    """
    List all legal documents with pagination.

    Browse the entire document collection with optional full content inclusion.

    Args:
        limit: Number of documents per page (default: 50, max: 100)
        offset: Pagination offset (default: 0)
        include_content: Include full content in results (default: False, only summaries)

    Returns:
        Dictionary with paginated list of all documents, including total count and pagination info

    Usage Tips:
        - Set include_content=False (default) for faster browsing with summaries
        - Set include_content=True when you need full document text
        - Use offset to navigate through pages (e.g., offset=50 for page 2)

    Examples:
        - First page with summaries: limit=50, offset=0, include_content=False
        - Second page with full content: limit=50, offset=50, include_content=True
    """
    try:
        return list_documents(
            limit=limit,
            offset=offset,
            include_content=include_content,
            config=config
        )
    except Exception as e:
        return create_error_response(
            error_type="list_error",
            message=f"Listing failed: {str(e)}"
        )


# Add health check endpoint for external monitoring
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy",
        "service": "LegalDocumentRAGServer",
        "version": "1.0.0"
    })


# Add root endpoint to show server info
@mcp.custom_route("/", methods=["GET"])
async def root(request):
    """Root endpoint showing server information."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "service": "Legal RAG MCP Server",
        "status": "running",
        "description": "FastMCP server for legal document search and retrieval",
        "endpoints": {
            "health": "/health",
            "mcp": "Use an MCP client to connect to this server"
        }
    })


if __name__ == "__main__":
    import sys

    # Check if we should run in HTTP mode (for remote access via Coolify)
    # HTTP mode: python legal_rag_server.py --http
    # Stdio mode: python legal_rag_server.py (default, for local use)
    if "--http" in sys.argv:
        import uvicorn
        from api_key_auth import APIKeyConfig, APIKeyMiddleware

        # Get port and host from environment variables with defaults
        port = int(os.getenv("PORT", "3000"))
        host = os.getenv("HOST", "0.0.0.0")

        # Check if database-backed authentication is enabled
        db_auth_enabled = os.getenv("MCP_API_AUTH_DB_ENABLED", "false").lower() == "true"

        # Load API key authentication configuration
        auth_config = APIKeyConfig.from_env()

        # Initialize database client if DB mode is enabled
        db_client = None
        if db_auth_enabled:
            try:
                from api_key_auth_db import create_api_key_db

                # Reuse existing Supabase connection
                supabase_client = get_cached_supabase_client(config)
                db_client = create_api_key_db(supabase_client)

                logger.info("Database-backed API key authentication ENABLED")
                logger.info("Using Supabase for API key storage, validation, and rate limiting")
            except Exception as e:
                logger.error(f"Failed to initialize database authentication: {e}")
                logger.warning("Falling back to environment variable authentication")
                db_auth_enabled = False

        # Log authentication status
        if db_auth_enabled:
            # Database mode logging handled above
            pass
        elif auth_config.enabled:
            logger.info("Environment variable-based API key authentication ENABLED")
            logger.info(f"Configured with {len(auth_config.api_keys)} valid API key(s)")
            if auth_config.key_names:
                logger.info(f"Named keys: {', '.join(auth_config.key_names.values())}")
        else:
            logger.warning("API Key authentication DISABLED")
            logger.warning("HTTP server is PUBLICLY accessible without authentication!")

        logger.info("Starting Legal RAG Server in HTTP mode")
        logger.info(f"Server will be accessible at http://{host}:{port}")

        # Get the ASGI app and add authentication middleware if enabled
        app = mcp.streamable_http_app()

        if db_auth_enabled or auth_config.enabled:
            # Add middleware with optional database client
            app.add_middleware(APIKeyMiddleware, config=auth_config, db_client=db_client)
            logger.info("APIKeyMiddleware added to request pipeline")

        uvicorn.run(app, host=host, port=port)
    else:
        logger.info("Starting Legal RAG Server in stdio mode (local use)")
        logger.info("No authentication required for stdio mode")
        mcp.run()
