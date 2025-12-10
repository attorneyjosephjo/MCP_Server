"""
Quick test script to verify Issue 24 fix
Tests that search completes in <15 seconds (not 4 minutes)
"""
import asyncio
import time
from dotenv import load_dotenv
from legal_rag_utils import LegalRAGConfig, search_documents_with_rerank

# Load environment variables
load_dotenv()

async def test_search_timing():
    """Test that search completes quickly"""
    print("Loading configuration...")
    config = LegalRAGConfig.from_env()
    config.validate()
    print(f"[OK] Configuration loaded")
    print(f"  - Supabase URL: {config.supabase_url}")
    print(f"  - Table: {config.table_name}")
    print(f"  - Match function: {config.match_function}")
    print()

    # Test query
    query = "SAFE agreement templates for startups"
    print(f"Testing search with query: '{query}'")
    print(f"Expected total time: 7-11 seconds")
    print(f"If Issue 24 not fixed: 240+ seconds")
    print()

    # Start timer
    start_time = time.time()
    print(f"[{0:.1f}s] Starting search...")

    # Perform search
    try:
        results = await search_documents_with_rerank(
            query=query,
            top_k=5,
            document_type=None,
            config=config
        )

        # Calculate elapsed time
        elapsed = time.time() - start_time
        print(f"[{elapsed:.1f}s] Search completed!")
        print()

        # Display results
        if "error_type" in results:
            print(f"❌ Error: {results['message']}")
            print(f"   Details: {results.get('details', {})}")
        else:
            print(f"✓ Success!")
            print(f"  - Total results: {results['total_results']}")
            print(f"  - Query: {results['query']}")
            print(f"  - Elapsed time: {elapsed:.2f} seconds")
            print()

            # Show first result
            if results['results']:
                first = results['results'][0]
                print(f"  First result:")
                print(f"    - Relevance score: {first.get('relevance_score', 'N/A')}")
                print(f"    - Type: {first.get('metadata', {}).get('type', 'N/A')}")
                print(f"    - Content preview: {first.get('content', '')[:100]}...")
            print()

        # Verdict
        if elapsed < 15:
            print(f"✅ PASS: Search completed in {elapsed:.2f}s (< 15s threshold)")
            print(f"✅ Issue 24 appears to be FIXED!")
        else:
            print(f"❌ FAIL: Search took {elapsed:.2f}s (> 15s threshold)")
            print(f"❌ Issue 24 may still be present")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{elapsed:.1f}s] Exception occurred!")
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        print()

        if elapsed > 200:
            print(f"⚠️  Request timed out after {elapsed:.2f}s")
            print(f"⚠️  Issue 24 likely still present")

if __name__ == "__main__":
    print("=" * 60)
    print("Issue 24 Fix Verification Test")
    print("=" * 60)
    print()

    asyncio.run(test_search_timing())

    print()
    print("=" * 60)
    print("Test complete")
    print("=" * 60)
