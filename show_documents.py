"""
Show actual document titles and metadata from RAG search results
"""
import asyncio
import sys
import os
import json

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

sys.path.insert(0, os.path.dirname(__file__))

from legal_rag_utils import LegalRAGConfig, search_documents_with_rerank
from dotenv import load_dotenv

load_dotenv()

async def show_documents():
    """Perform search and display document details"""
    config = LegalRAGConfig.from_env()

    # Test search
    query = "What are the key terms in a SAFE agreement?"
    print(f"Query: {query}\n")
    print("=" * 80)

    result = await search_documents_with_rerank(
        query=query,
        top_k=10,
        document_type=None,
        config=config
    )

    print(f"Total Results: {result.get('total_results', 0)}\n")

    if result.get('results'):
        for i, doc in enumerate(result['results'], 1):
            metadata = doc.get('metadata', {})

            print(f"\n{i}. Document ID: {doc.get('id')}")

            # Try to get document name from metadata
            doc_name = metadata.get('doc_name', metadata.get('title', 'Untitled'))
            print(f"   Document Name: {doc_name}")

            doc_type = metadata.get('legaldocument_type', metadata.get('type', 'unknown'))
            print(f"   Document Type: {doc_type}")

            # Show categories if available
            if 'main_category' in metadata:
                print(f"   Category: {metadata.get('main_category')} / {metadata.get('sub_category', 'N/A')}")

            if 'jurisdiction' in metadata:
                print(f"   Jurisdiction: {metadata.get('jurisdiction')}")

            print(f"   Relevance Score: {doc.get('relevance_score', 0):.4f}")
            print(f"   Similarity: {doc.get('similarity', 0):.4f}")

            # Show file summary if available
            if 'file_summary' in metadata:
                summary = metadata.get('file_summary', '')
                print(f"   Summary: {summary[:200]}...")

            print(f"   Created: {metadata.get('created_at', metadata.get('retrieved_at', 'unknown'))}")

            # Show any additional metadata
            other_meta = {k: v for k, v in metadata.items()
                         if k not in ['title', 'type', 'created_at']}
            if other_meta:
                print(f"   Other metadata: {other_meta}")

            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(show_documents())
