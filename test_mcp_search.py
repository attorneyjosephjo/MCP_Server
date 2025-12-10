"""
Test the MCP server's semantic search tool directly
"""
import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from legal_rag_utils import LegalRAGConfig, search_documents_with_rerank
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

def log(message: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

async def test_mcp_search():
    """Test the actual MCP search function"""
    log("=" * 60)
    log("MCP Server Search Tool Test")
    log("=" * 60)

    # Load config
    log("Loading configuration...")
    config = LegalRAGConfig.from_env()
    config.validate()
    log(f"Config loaded: {config.supabase_url}")

    # Test search
    query = "What are the key terms in a SAFE agreement?"
    log(f"\nQuery: {query}")
    log(f"top_k: 10")
    log(f"document_type: None")

    log("\nStarting search...")
    start_time = time.time()

    try:
        result = await search_documents_with_rerank(
            query=query,
            top_k=10,
            document_type=None,
            config=config
        )

        elapsed = time.time() - start_time

        log("\n" + "=" * 60)
        log("SEARCH COMPLETED")
        log("=" * 60)
        log(f"Total Time: {elapsed:.2f} seconds")
        log(f"Results: {result.get('total_results', 0)} documents")

        if result.get('results'):
            top_result = result['results'][0]
            log(f"\nTop result:")
            log(f"  - Relevance Score: {top_result.get('relevance_score', 0):.4f}")
            log(f"  - Similarity: {top_result.get('similarity', 0):.4f}")
            log(f"  - Content Preview: {top_result.get('content', '')[:100]}...")

        # Performance check
        log("\n" + "=" * 60)
        if elapsed > 30:
            log("[FAIL] Search took longer than expected!")
            log(f"  Expected: < 30 seconds")
            log(f"  Actual: {elapsed:.2f} seconds")
        elif elapsed > 15:
            log("[WARN] Search took longer than ideal")
            log(f"  Ideal: 7-11 seconds")
            log(f"  Actual: {elapsed:.2f} seconds")
        else:
            log("[PASS] Search completed within expected time!")
            log(f"  Target: 7-11 seconds")
            log(f"  Actual: {elapsed:.2f} seconds")
        log("=" * 60)

    except Exception as e:
        elapsed = time.time() - start_time
        log(f"\n[ERROR] Search failed after {elapsed:.2f} seconds")
        log(f"Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_search())
