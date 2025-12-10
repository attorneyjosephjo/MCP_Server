from dataclasses import dataclass
from datetime import datetime
from functools import wraps, lru_cache
import asyncio
import logging
import os
import time
import uuid
from typing import Optional, List, Dict, Any

from supabase import create_client, Client
from openai import AsyncOpenAI, OpenAI
import cohere

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('legal_rag_server.log')
    ]
)
logger = logging.getLogger('legal_rag')


@dataclass
class LegalRAGConfig:
    """Configuration for Legal RAG Server"""
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    cohere_api_key: str
    table_name: str = "n8n_law_startuplaw"
    match_function: str = "match_n8n_law_startuplaw"
    top_k: int = 10
    embedding_model: str = "text-embedding-3-small"
    rerank_model: str = "rerank-v3.5"
    match_threshold: float = 0.5  # Minimum similarity threshold for vector search

    @classmethod
    def from_env(cls) -> 'LegalRAGConfig':
        """Load configuration from environment variables"""
        required_keys = [
            'SUPABASE_URL',
            'SUPABASE_SERVICE_ROLE_KEY',
            'OPENAI_API_KEY',
            'COHERE_API_KEY'
        ]

        missing = [key for key in required_keys if not os.getenv(key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        return cls(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            cohere_api_key=os.getenv('COHERE_API_KEY'),
            table_name=os.getenv('LEGAL_RAG_TABLE_NAME', 'n8n_law_startuplaw'),
            match_function=os.getenv('LEGAL_RAG_MATCH_FUNCTION', 'match_n8n_law_startuplaw'),
            top_k=int(os.getenv('LEGAL_RAG_TOP_K', '10')),
            match_threshold=float(os.getenv('LEGAL_RAG_MATCH_THRESHOLD', '0.5')),
        )

    def validate(self) -> None:
        """Validate configuration"""
        if not (self.supabase_url.startswith('https://') or self.supabase_url.startswith('http://')):
            raise ValueError("Supabase URL must start with http:// or https://")

        if self.top_k < 1 or self.top_k > 10:
            raise ValueError("top_k must be between 1 and 10")

        if self.match_threshold < 0.0 or self.match_threshold > 1.0:
            raise ValueError("match_threshold must be between 0.0 and 1.0")


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 2):
    """Decorator for retrying failed API calls with exponential backoff (sync version)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s... Error: {e}")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator


def async_retry_with_backoff(max_retries: int = 3, backoff_factor: float = 2):
    """Decorator for retrying failed API calls with exponential backoff (async version)"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s... Error: {e}")
                    await asyncio.sleep(wait_time)
            return None
        return wrapper
    return decorator


def create_error_response(error_type: str, message: str, details: Optional[Dict] = None) -> Dict:
    """Standardized error response format"""
    return {
        "error": True,
        "error_type": error_type,
        "message": message,
        "details": details or {},
        "timestamp": str(datetime.now())
    }


@lru_cache(maxsize=1)
def get_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """
    Initialize and return Supabase client with caching
    Note: Uses LRU cache to reuse client across requests
    """
    logger.info("Creating new Supabase client")
    return create_client(supabase_url, supabase_key)


def get_cached_supabase_client(config: LegalRAGConfig) -> Client:
    """Helper to get cached Supabase client from config"""
    return get_supabase_client(config.supabase_url, config.supabase_key)


@retry_with_backoff(max_retries=3)
def generate_embedding(text: str, config: LegalRAGConfig) -> List[float]:
    """
    Generate embedding using OpenAI text-embedding-3-small (sync version)
    Returns 1536-dimensional vector
    """
    client = OpenAI(api_key=config.openai_api_key)

    response = client.embeddings.create(
        input=text,
        model=config.embedding_model
    )

    return response.data[0].embedding


@async_retry_with_backoff(max_retries=3)
async def generate_embedding_async(text: str, config: LegalRAGConfig) -> List[float]:
    """
    Generate embedding using OpenAI text-embedding-3-small (async version)
    Returns 1536-dimensional vector

    IMPORTANT: Uses context manager to properly close AsyncOpenAI client connections.
    Without this, the client waits for connection timeout (240 seconds).
    """
    logger.debug("Creating AsyncOpenAI client...")
    async with AsyncOpenAI(api_key=config.openai_api_key) as client:
        logger.debug(f"Calling embeddings API with model: {config.embedding_model}")
        response = await client.embeddings.create(
            input=text,
            model=config.embedding_model
        )
        logger.debug("Embeddings API call completed, extracting embedding...")
        embedding = response.data[0].embedding
        logger.debug(f"Embedding extracted, length: {len(embedding)}")

    logger.debug("AsyncOpenAI client closed, returning embedding")
    return embedding


@retry_with_backoff(max_retries=3)
def rerank_documents(
    query: str,
    documents: List[Dict],
    top_n: int,
    config: LegalRAGConfig
) -> List[Dict]:
    """
    Rerank documents using Cohere rerank-v3.5 (sync version)
    Returns list of documents with relevance scores
    """
    if not documents:
        return []

    co = cohere.ClientV2(api_key=config.cohere_api_key)

    # Extract content for reranking
    doc_texts = [doc['content'] for doc in documents]

    rerank_response = co.rerank(
        model=config.rerank_model,
        query=query,
        documents=doc_texts,
        top_n=min(top_n, len(documents))
    )

    # Map reranked indices back to original documents
    reranked_results = []
    for item in rerank_response.results:
        doc = documents[item.index].copy()
        doc['relevance_score'] = item.relevance_score
        reranked_results.append(doc)

    return reranked_results


@async_retry_with_backoff(max_retries=3)
async def rerank_documents_async(
    query: str,
    documents: List[Dict],
    top_n: int,
    config: LegalRAGConfig
) -> List[Dict]:
    """
    Rerank documents using Cohere rerank-v3.5 (async version)
    Returns list of documents with relevance scores
    Note: Runs in thread pool since Cohere client is sync-only
    """
    if not documents:
        return []

    # Run sync Cohere call in thread pool to avoid blocking
    def _rerank():
        logger.debug("Creating Cohere ClientV2...")
        co = cohere.ClientV2(api_key=config.cohere_api_key)
        doc_texts = [doc['content'] for doc in documents]
        logger.debug(f"Calling Cohere rerank with {len(doc_texts)} documents, top_n={min(top_n, len(documents))}")
        result = co.rerank(
            model=config.rerank_model,
            query=query,
            documents=doc_texts,
            top_n=min(top_n, len(documents))
        )
        logger.debug("Cohere rerank API call completed")
        # Explicitly close the client to release resources
        if hasattr(co, 'close'):
            co.close()
            logger.debug("Cohere client closed")
        return result

    rerank_response = await asyncio.to_thread(_rerank)

    # Map reranked indices back to original documents
    reranked_results = []
    for item in rerank_response.results:
        doc = documents[item.index].copy()
        doc['relevance_score'] = item.relevance_score
        reranked_results.append(doc)

    return reranked_results


async def search_documents_with_rerank(
    query: str,
    top_k: int,
    document_type: Optional[str],
    config: LegalRAGConfig
) -> Dict[str, Any]:
    """
    Semantic search with vector similarity and Cohere reranking

    Args:
        query: Natural language search query
        top_k: Number of results to return
        document_type: Optional filter - "practice_guide", "agreement", or "clause"
        config: LegalRAGConfig instance

    Returns:
        Dictionary with search results and relevance scores
    """
    try:
        # Generate query embedding (async)
        logger.info(f"Starting embedding generation for query: {query[:50]}...")
        query_embedding = await generate_embedding_async(query, config)
        logger.info(f"Embedding generated successfully, length: {len(query_embedding)}")

        # Perform vector search via Supabase RPC (run in thread pool)
        logger.info("Starting Supabase vector search...")
        def _vector_search():
            logger.info("Inside _vector_search, getting Supabase client...")
            supabase = get_cached_supabase_client(config)
            search_count = 15  # Retrieve 15 candidates for reranker
            logger.info(f"Calling RPC function: {config.match_function} with count: {search_count}")
            return supabase.rpc(
                config.match_function,
                {
                    'query_embedding': query_embedding,
                    'match_threshold': config.match_threshold,
                    'match_count': search_count
                }
            ).execute()

        logger.info("About to call asyncio.to_thread(_vector_search)...")
        results = await asyncio.to_thread(_vector_search)
        logger.info(f"Supabase search completed, got {len(results.data) if results.data else 0} results")

        if not results.data:
            return {
                "query": query,
                "total_results": 0,
                "results": [],
                "message": "No documents found matching your query"
            }

        # Filter by document type if provided
        filtered_results = results.data
        if document_type:
            filtered_results = [
                r for r in filtered_results
                if r.get('metadata', {}).get('type') == document_type
            ]

            if not filtered_results:
                return {
                    "query": query,
                    "document_type": document_type,
                    "total_results": 0,
                    "results": [],
                    "message": f"No {document_type} documents found matching your query"
                }

        # Rerank with Cohere (async)
        logger.info(f"Starting Cohere reranking with {len(filtered_results)} documents...")
        try:
            reranked_results = await rerank_documents_async(
                query=query,
                documents=filtered_results,
                top_n=min(top_k, 5),  # Cap at 5 documents for Claude context window
                config=config
            )
            logger.info(f"Reranking completed, returning {len(reranked_results)} results")
        except Exception as e:
            # Fall back to vector similarity scores if reranking fails
            logger.warning(f"Reranking failed: {e}. Falling back to vector similarity scores.")
            reranked_results = filtered_results[:min(top_k, 5)]  # Cap at 5 documents
            for doc in reranked_results:
                doc['relevance_score'] = doc.get('similarity', 0.0)

        logger.info("Returning final results...")
        return {
            "query": query,
            "document_type": document_type,
            "total_results": len(reranked_results),
            "results": reranked_results
        }

    except Exception as e:
        return create_error_response(
            error_type="search_error",
            message=f"Search failed: {str(e)}"
        )


def browse_by_type(
    document_type: str,
    limit: int,
    offset: int,
    config: LegalRAGConfig
) -> Dict[str, Any]:
    """
    Browse documents filtered by type with pagination

    Args:
        document_type: Type of document - "practice_guide", "agreement", or "clause"
        limit: Number of documents per page
        offset: Pagination offset
        config: LegalRAGConfig instance

    Returns:
        Dictionary with paginated documents
    """
    try:
        # Validate document type
        VALID_TYPES = ['practice_guide', 'agreement', 'clause']
        if document_type not in VALID_TYPES:
            return create_error_response(
                error_type="validation_error",
                message=f"Invalid document type. Must be one of: {VALID_TYPES}"
            )

        # Validate and clamp pagination
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        # Query Supabase with filter
        supabase = get_cached_supabase_client(config)

        result = supabase.table(config.table_name) \
            .select('id, content, metadata') \
            .eq('metadata->>type', document_type) \
            .range(offset, offset + limit - 1) \
            .order('metadata->>created_at', desc=True) \
            .execute()

        # Extract summaries (first 200 chars)
        documents = []
        for doc in result.data:
            documents.append({
                'id': doc['id'],
                'type': doc['metadata'].get('type'),
                'title': doc['metadata'].get('title', 'Untitled'),
                'summary': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                'metadata': doc['metadata']
            })

        return {
            "document_type": document_type,
            "page_size": limit,
            "offset": offset,
            "count": len(documents),
            "has_more": len(documents) == limit,
            "documents": documents
        }

    except Exception as e:
        return create_error_response(
            error_type="browse_error",
            message=f"Browse operation failed: {str(e)}"
        )


def get_document(
    document_id: str,
    config: LegalRAGConfig
) -> Dict[str, Any]:
    """
    Retrieve a specific legal document by UUID

    Args:
        document_id: UUID of the document
        config: LegalRAGConfig instance

    Returns:
        Complete document with full content and metadata
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(document_id)
        except ValueError:
            return create_error_response(
                error_type="validation_error",
                message="Invalid document ID format. Must be a valid UUID."
            )

        # Fetch from Supabase
        supabase = get_cached_supabase_client(config)

        result = supabase.table(config.table_name) \
            .select('*') \
            .eq('id', document_id) \
            .execute()

        # Handle not found
        if not result.data or len(result.data) == 0:
            return create_error_response(
                error_type="not_found",
                message=f"Document not found with ID: {document_id}",
                details={"suggestion": "Use list_all_legal_documents to browse available documents"}
            )

        document = result.data[0]
        return {
            "id": document['id'],
            "content": document['content'],
            "metadata": document.get('metadata', {}),
            "retrieved_at": str(datetime.now())
        }

    except Exception as e:
        return create_error_response(
            error_type="retrieval_error",
            message=f"Document retrieval failed: {str(e)}"
        )


def list_documents(
    limit: int,
    offset: int,
    include_content: bool,
    config: LegalRAGConfig
) -> Dict[str, Any]:
    """
    List all legal documents with pagination

    Args:
        limit: Number of documents per page (max 100)
        offset: Pagination offset
        include_content: Include full content in results
        config: LegalRAGConfig instance

    Returns:
        Dictionary with paginated list of all documents
    """
    try:
        # Validate and clamp pagination
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        # Query Supabase
        supabase = get_cached_supabase_client(config)

        # Select fields based on include_content flag
        fields = 'id, content, metadata' if include_content else 'id, metadata'

        # Get documents with count
        result = supabase.table(config.table_name) \
            .select(fields, count='exact') \
            .range(offset, offset + limit - 1) \
            .order('metadata->>created_at', desc=True) \
            .execute()

        total_count = result.count if result.count is not None else 0

        # Format response
        documents = []
        for doc in result.data:
            doc_data = {
                'id': doc['id'],
                'title': doc['metadata'].get('title', 'Untitled'),
                'type': doc['metadata'].get('type', 'unknown'),
                'metadata': doc['metadata']
            }

            if include_content:
                doc_data['content'] = doc.get('content', '')
            else:
                # When content is not selected, try to get summary from metadata
                summary = doc.get('metadata', {}).get('summary', '')
                if summary:
                    doc_data['summary'] = summary[:200] + '...' if len(summary) > 200 else summary
                else:
                    doc_data['summary'] = '[No summary available]'

            documents.append(doc_data)

        return {
            "total_documents": total_count,
            "page_size": limit,
            "offset": offset,
            "current_page": (offset // limit) + 1,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
            "has_more": offset + limit < total_count,
            "documents": documents
        }

    except Exception as e:
        return create_error_response(
            error_type="list_error",
            message=f"List operation failed: {str(e)}"
        )
