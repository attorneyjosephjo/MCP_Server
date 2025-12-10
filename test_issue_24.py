"""
Test script for Issue 24: Mysterious 4-Minute Delay
Tests each component of the search pipeline individually with timing
"""
import asyncio
import time
from datetime import datetime
from openai import AsyncOpenAI
import cohere
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

def log(message: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

async def test_openai_embedding():
    """Test OpenAI embedding generation with timing"""
    log("=" * 60)
    log("TEST 1: OpenAI Embedding Generation")
    log("=" * 60)

    query = "What are the key terms in a SAFE agreement?"

    log(f"Query: {query}")
    log("Creating AsyncOpenAI client with context manager...")

    start = time.time()

    async with AsyncOpenAI(api_key=OPENAI_API_KEY) as client:
        log("Client created, calling embeddings API...")
        response = await client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        log("API call completed, extracting embedding...")
        embedding = response.data[0].embedding
        log(f"Embedding extracted, length: {len(embedding)}")

    elapsed = time.time() - start
    log(f"[OK] OpenAI embedding completed in {elapsed:.2f} seconds")
    log(f"[OK] Client properly closed via context manager")

    return embedding

async def test_supabase_vector_search(query_embedding):
    """Test Supabase vector search with timing"""
    log("\n" + "=" * 60)
    log("TEST 2: Supabase Vector Search")
    log("=" * 60)

    log(f"Supabase URL: {SUPABASE_URL}")
    log(f"Creating Supabase client...")

    start = time.time()

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    log("Client created, calling RPC function...")

    result = supabase.rpc(
        'match_n8n_law_startuplaw',
        {
            'query_embedding': query_embedding,
            'match_threshold': 0.5,
            'match_count': 20
        }
    ).execute()

    elapsed = time.time() - start
    log(f"[OK] Supabase search completed in {elapsed:.2f} seconds")
    log(f"[OK] Found {len(result.data)} documents")

    if result.data:
        log(f"[OK] Sample result ID: {result.data[0].get('id')}")
        log(f"[OK] Sample similarity: {result.data[0].get('similarity', 0):.4f}")

    return result.data

async def test_cohere_reranking(query, documents):
    """Test Cohere reranking with timing"""
    log("\n" + "=" * 60)
    log("TEST 3: Cohere Reranking")
    log("=" * 60)

    if not documents:
        log("[WARN] No documents to rerank")
        return []

    log(f"Query: {query}")
    log(f"Documents to rerank: {len(documents)}")
    log("Creating Cohere client...")

    start = time.time()

    co = cohere.ClientV2(api_key=COHERE_API_KEY)
    log("Client created, extracting document texts...")

    doc_texts = [doc['content'] for doc in documents]
    log(f"Calling rerank API with top_n=10...")

    rerank_response = co.rerank(
        model="rerank-v3.5",
        query=query,
        documents=doc_texts,
        top_n=min(10, len(documents))
    )

    elapsed = time.time() - start
    log(f"[OK] Cohere reranking completed in {elapsed:.2f} seconds")
    log(f"[OK] Returned {len(rerank_response.results)} ranked results")

    if rerank_response.results:
        top_result = rerank_response.results[0]
        log(f"[OK] Top result relevance score: {top_result.relevance_score:.4f}")

    # Explicitly close client
    if hasattr(co, 'close'):
        co.close()
        log("[OK] Cohere client closed")

    return rerank_response.results

async def test_full_pipeline():
    """Test the full search pipeline end-to-end"""
    log("\n" + "=" * 60)
    log("TEST 4: Full Pipeline End-to-End")
    log("=" * 60)

    query = "What are the key terms in a SAFE agreement?"

    total_start = time.time()

    # Step 1: Generate embedding
    log("STEP 1: Generating embedding...")
    step1_start = time.time()
    embedding = await test_openai_embedding()
    step1_time = time.time() - step1_start

    # Small delay to see if there's any hidden waiting
    await asyncio.sleep(0.1)

    # Step 2: Vector search
    log("\nSTEP 2: Performing vector search...")
    step2_start = time.time()
    documents = await test_supabase_vector_search(embedding)
    step2_time = time.time() - step2_start

    # Small delay to see if there's any hidden waiting
    await asyncio.sleep(0.1)

    # Step 3: Reranking
    log("\nSTEP 3: Reranking results...")
    step3_start = time.time()
    reranked = await test_cohere_reranking(query, documents)
    step3_time = time.time() - step3_start

    total_time = time.time() - total_start

    # Summary
    log("\n" + "=" * 60)
    log("TIMING SUMMARY")
    log("=" * 60)
    log(f"Step 1 (OpenAI Embedding):  {step1_time:.2f}s")
    log(f"Step 2 (Supabase Search):   {step2_time:.2f}s")
    log(f"Step 3 (Cohere Reranking):  {step3_time:.2f}s")
    log("-" * 60)
    log(f"Total Pipeline Time:        {total_time:.2f}s")
    log("=" * 60)

    if total_time > 30:
        log("[WARN] WARNING: Pipeline took longer than expected!")
        log("[WARN] Expected: 7-11 seconds")
        log(f"[WARN] Actual: {total_time:.2f} seconds")
    else:
        log("[OK] SUCCESS: Pipeline completed within expected time!")

    return total_time

async def main():
    """Run all tests"""
    log("Starting Issue 24 Debug Tests")
    log(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")

    try:
        # Run individual component tests first
        embedding = await test_openai_embedding()
        await asyncio.sleep(0.5)  # Small delay between tests

        documents = await test_supabase_vector_search(embedding)
        await asyncio.sleep(0.5)

        if documents:
            query = "What are the key terms in a SAFE agreement?"
            await test_cohere_reranking(query, documents)
            await asyncio.sleep(0.5)

        # Run full pipeline test
        # total_time = await test_full_pipeline()

        log("\n" + "=" * 60)
        log("ALL TESTS COMPLETED")
        log("=" * 60)

    except Exception as e:
        log(f"\n[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
