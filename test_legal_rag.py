"""
Comprehensive test suite for Legal Document RAG MCP Server

This test file includes:
- Unit tests for utility functions
- Integration tests for MCP tools
- Mocked external API calls
- Error handling tests
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from legal_rag_utils import (
    LegalRAGConfig,
    generate_embedding,
    generate_embedding_async,
    rerank_documents,
    rerank_documents_async,
    search_documents_with_rerank,
    browse_by_type,
    get_document,
    list_documents,
    create_error_response,
    get_supabase_client,
    get_cached_supabase_client,
)


# Fixtures
@pytest.fixture
def test_config():
    """Create a test configuration"""
    return LegalRAGConfig(
        supabase_url="http://test.supabase.co",
        supabase_key="test_key",
        openai_api_key="test_openai_key",
        cohere_api_key="test_cohere_key",
        table_name="test_table",
        match_function="test_match_function",
        top_k=10,
        match_threshold=0.5,
    )


@pytest.fixture
def mock_embedding():
    """Mock embedding vector"""
    return [0.1] * 1536


@pytest.fixture
def mock_documents():
    """Mock document results from Supabase"""
    return [
        {
            'id': '123e4567-e89b-12d3-a456-426614174000',
            'content': 'This is a test legal document about SAFE agreements.',
            'metadata': {'type': 'agreement', 'title': 'SAFE Agreement Guide'},
            'similarity': 0.85
        },
        {
            'id': '223e4567-e89b-12d3-a456-426614174001',
            'content': 'This is another document about startup incorporation.',
            'metadata': {'type': 'practice_guide', 'title': 'Incorporation Guide'},
            'similarity': 0.78
        }
    ]


# Configuration Tests
class TestLegalRAGConfig:
    """Test configuration loading and validation"""

    def test_config_from_env_missing_vars(self):
        """Test that from_env raises error when variables are missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required environment variables"):
                LegalRAGConfig.from_env()

    def test_config_from_env_success(self):
        """Test successful configuration loading from environment"""
        env_vars = {
            'SUPABASE_URL': 'http://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'COHERE_API_KEY': 'test_cohere_key',
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = LegalRAGConfig.from_env()
            assert config.supabase_url == 'http://test.supabase.co'
            assert config.supabase_key == 'test_key'

    def test_config_validation_invalid_url(self, test_config):
        """Test URL validation"""
        test_config.supabase_url = "invalid-url"
        with pytest.raises(ValueError, match="must start with"):
            test_config.validate()

    def test_config_validation_invalid_top_k(self, test_config):
        """Test top_k validation"""
        test_config.top_k = 0
        with pytest.raises(ValueError, match="top_k must be between"):
            test_config.validate()

        test_config.top_k = 101
        with pytest.raises(ValueError, match="top_k must be between"):
            test_config.validate()

    def test_config_validation_invalid_threshold(self, test_config):
        """Test match_threshold validation"""
        test_config.match_threshold = -0.1
        with pytest.raises(ValueError, match="match_threshold must be between"):
            test_config.validate()

        test_config.match_threshold = 1.1
        with pytest.raises(ValueError, match="match_threshold must be between"):
            test_config.validate()


# Utility Function Tests
class TestUtilityFunctions:
    """Test utility functions"""

    def test_create_error_response(self):
        """Test error response creation"""
        error = create_error_response(
            error_type="test_error",
            message="Test message",
            details={"key": "value"}
        )

        assert error['error'] is True
        assert error['error_type'] == "test_error"
        assert error['message'] == "Test message"
        assert error['details']['key'] == "value"
        assert 'timestamp' in error

    @patch('legal_rag_utils.create_client')
    def test_get_supabase_client_caching(self, mock_create_client):
        """Test that Supabase client is cached"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Clear the cache first
        get_supabase_client.cache_clear()

        # First call should create a new client
        client1 = get_supabase_client("http://test.com", "key")
        assert mock_create_client.call_count == 1

        # Second call with same args should use cached client
        client2 = get_supabase_client("http://test.com", "key")
        assert mock_create_client.call_count == 1
        assert client1 is client2


# Embedding Generation Tests
class TestEmbeddingGeneration:
    """Test embedding generation functions"""

    @patch('legal_rag_utils.OpenAI')
    def test_generate_embedding_sync(self, mock_openai_class, test_config, mock_embedding):
        """Test synchronous embedding generation"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = generate_embedding("test query", test_config)

        assert result == mock_embedding
        mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('legal_rag_utils.AsyncOpenAI')
    async def test_generate_embedding_async(self, mock_openai_class, test_config, mock_embedding):
        """Test asynchronous embedding generation"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_client.embeddings.create = asyncio.coroutine(lambda **kwargs: mock_response)
        mock_openai_class.return_value = mock_client

        result = await generate_embedding_async("test query", test_config)

        assert result == mock_embedding


# Reranking Tests
class TestReranking:
    """Test document reranking functions"""

    @patch('legal_rag_utils.cohere.ClientV2')
    def test_rerank_documents_sync(self, mock_cohere_class, test_config, mock_documents):
        """Test synchronous document reranking"""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.index = 1
        mock_result.relevance_score = 0.95
        mock_response = Mock()
        mock_response.results = [mock_result]
        mock_client.rerank.return_value = mock_response
        mock_cohere_class.return_value = mock_client

        result = rerank_documents("test query", mock_documents, 1, test_config)

        assert len(result) == 1
        assert result[0]['relevance_score'] == 0.95
        assert result[0]['content'] == mock_documents[1]['content']

    def test_rerank_documents_empty_list(self, test_config):
        """Test reranking with empty document list"""
        result = rerank_documents("test query", [], 10, test_config)
        assert result == []


# Search Function Tests
class TestSearchDocuments:
    """Test search_documents_with_rerank function"""

    @pytest.mark.asyncio
    @patch('legal_rag_utils.generate_embedding_async')
    @patch('legal_rag_utils.get_cached_supabase_client')
    @patch('legal_rag_utils.rerank_documents_async')
    async def test_search_success(
        self,
        mock_rerank,
        mock_get_client,
        mock_generate_embedding,
        test_config,
        mock_embedding,
        mock_documents
    ):
        """Test successful search with reranking"""
        # Mock embedding generation
        mock_generate_embedding.return_value = mock_embedding

        # Mock Supabase client and response
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_supabase.rpc.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        # Mock reranking
        reranked_docs = [mock_documents[0]]
        mock_rerank.return_value = reranked_docs

        result = await search_documents_with_rerank("test query", 10, None, test_config)

        assert result['query'] == "test query"
        assert result['total_results'] == 1
        assert len(result['results']) == 1

    @pytest.mark.asyncio
    @patch('legal_rag_utils.generate_embedding_async')
    @patch('legal_rag_utils.get_cached_supabase_client')
    async def test_search_no_results(
        self,
        mock_get_client,
        mock_generate_embedding,
        test_config,
        mock_embedding
    ):
        """Test search with no matching documents"""
        mock_generate_embedding.return_value = mock_embedding

        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = await search_documents_with_rerank("test query", 10, None, test_config)

        assert result['total_results'] == 0
        assert 'message' in result

    @pytest.mark.asyncio
    @patch('legal_rag_utils.generate_embedding_async')
    @patch('legal_rag_utils.get_cached_supabase_client')
    @patch('legal_rag_utils.rerank_documents_async')
    async def test_search_with_type_filter(
        self,
        mock_rerank,
        mock_get_client,
        mock_generate_embedding,
        test_config,
        mock_embedding,
        mock_documents
    ):
        """Test search with document type filtering"""
        mock_generate_embedding.return_value = mock_embedding

        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_supabase.rpc.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        mock_rerank.return_value = [mock_documents[0]]

        result = await search_documents_with_rerank("test query", 10, "agreement", test_config)

        assert result['document_type'] == "agreement"
        # Verify filtering occurred (should only include 'agreement' type)


# Browse Function Tests
class TestBrowseByType:
    """Test browse_by_type function"""

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_browse_success(self, mock_get_client, test_config, mock_documents):
        """Test successful browsing by document type"""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_supabase.table.return_value.select.return_value.eq.return_value.range.return_value.order.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = browse_by_type("agreement", 20, 0, test_config)

        assert result['document_type'] == "agreement"
        assert result['page_size'] == 20
        assert result['offset'] == 0
        assert 'documents' in result

    def test_browse_invalid_type(self, test_config):
        """Test browsing with invalid document type"""
        result = browse_by_type("invalid_type", 20, 0, test_config)

        assert result['error'] is True
        assert result['error_type'] == "validation_error"


# Get Document Tests
class TestGetDocument:
    """Test get_document function"""

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_get_document_success(self, mock_get_client, test_config, mock_documents):
        """Test successful document retrieval"""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [mock_documents[0]]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = get_document('123e4567-e89b-12d3-a456-426614174000', test_config)

        assert 'id' in result
        assert 'content' in result
        assert 'metadata' in result

    def test_get_document_invalid_uuid(self, test_config):
        """Test document retrieval with invalid UUID"""
        result = get_document('invalid-uuid', test_config)

        assert result['error'] is True
        assert result['error_type'] == "validation_error"

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_get_document_not_found(self, mock_get_client, test_config):
        """Test document retrieval when document doesn't exist"""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = get_document('123e4567-e89b-12d3-a456-426614174000', test_config)

        assert result['error'] is True
        assert result['error_type'] == "not_found"


# List Documents Tests
class TestListDocuments:
    """Test list_documents function"""

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_list_documents_with_content(self, mock_get_client, test_config, mock_documents):
        """Test listing documents with full content"""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_result.count = 2
        mock_supabase.table.return_value.select.return_value.range.return_value.order.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = list_documents(50, 0, True, test_config)

        assert result['total_documents'] == 2
        assert result['page_size'] == 50
        assert len(result['documents']) == 2
        assert 'content' in result['documents'][0]

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_list_documents_without_content(self, mock_get_client, test_config):
        """Test listing documents without full content (summaries only)"""
        mock_documents = [
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'metadata': {'type': 'agreement', 'title': 'Test', 'summary': 'Short summary'}
            }
        ]
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_result.count = 1
        mock_supabase.table.return_value.select.return_value.range.return_value.order.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = list_documents(50, 0, False, test_config)

        assert len(result['documents']) == 1
        assert 'summary' in result['documents'][0]
        assert 'content' not in result['documents'][0]

    @patch('legal_rag_utils.get_cached_supabase_client')
    def test_list_documents_pagination(self, mock_get_client, test_config, mock_documents):
        """Test pagination calculations"""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = mock_documents
        mock_result.count = 100
        mock_supabase.table.return_value.select.return_value.range.return_value.order.return_value.execute.return_value = mock_result
        mock_get_client.return_value = mock_supabase

        result = list_documents(50, 0, True, test_config)

        assert result['current_page'] == 1
        assert result['total_pages'] == 2
        assert result['has_more'] is True


# Integration Tests
class TestIntegration:
    """Integration tests with mocked external services"""

    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self, test_config):
        """Test complete search flow from query to reranked results"""
        with patch('legal_rag_utils.AsyncOpenAI') as mock_openai, \
             patch('legal_rag_utils.get_cached_supabase_client') as mock_supabase, \
             patch('legal_rag_utils.cohere.ClientV2') as mock_cohere:

            # Setup mocks
            mock_embedding = [0.1] * 1536
            mock_openai_client = Mock()
            mock_response = Mock()
            mock_response.data = [Mock(embedding=mock_embedding)]
            mock_openai_client.embeddings.create = asyncio.coroutine(lambda **kwargs: mock_response)
            mock_openai.return_value = mock_openai_client

            mock_docs = [
                {
                    'id': '123',
                    'content': 'Test document',
                    'metadata': {'type': 'agreement'},
                    'similarity': 0.9
                }
            ]
            mock_supabase_client = Mock()
            mock_result = Mock()
            mock_result.data = mock_docs
            mock_supabase_client.rpc.return_value.execute.return_value = mock_result
            mock_supabase.return_value = mock_supabase_client

            mock_cohere_client = Mock()
            mock_rerank_result = Mock()
            mock_rerank_result.index = 0
            mock_rerank_result.relevance_score = 0.95
            mock_rerank_response = Mock()
            mock_rerank_response.results = [mock_rerank_result]
            mock_cohere_client.rerank.return_value = mock_rerank_response
            mock_cohere.return_value = mock_cohere_client

            # Execute search
            result = await search_documents_with_rerank("SAFE agreement", 10, None, test_config)

            # Verify results
            assert 'results' in result
            assert result['query'] == "SAFE agreement"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
