from dotenv import load_dotenv
import logging
from mcp.server.fastmcp import FastMCP
from legal_rag_utils import (
    LegalRAGConfig,
    search_documents_with_rerank,
    browse_by_type,
    get_document,
    list_documents,
    create_error_response
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
        top_k: Number of results to return (default: 10, max: 100)
        document_type: Optional filter - "practice_guide", "agreement", or "clause"

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
        if top_k < 1 or top_k > 100:
            return create_error_response(
                error_type="validation_error",
                message="top_k must be between 1 and 100"
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
        document_type: Type of document - "practice_guide", "agreement", or "clause"
        limit: Number of documents per page (default: 20, max: 100)
        offset: Pagination offset (default: 0)

    Returns:
        Dictionary with paginated documents and metadata

    Document Types:
        - practice_guide: Step-by-step guides and how-to documents
        - agreement: Full legal agreement templates
        - clause: Individual contract clauses and provisions

    Examples:
        - Browse all agreement templates: document_type="agreement"
        - Get next page of practice guides: document_type="practice_guide", offset=20
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
        document_id: UUID of the document (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

    Returns:
        Complete document with full content and metadata

    Example:
        document_id="550e8400-e29b-41d4-a716-446655440000"
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


if __name__ == "__main__":
    mcp.run()
