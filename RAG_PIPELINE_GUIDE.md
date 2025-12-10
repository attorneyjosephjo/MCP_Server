# RAG Pipeline Guide
## Legal Document RAG Server - Document Retrieval & Reranking Process

---

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Configuration Parameters](#configuration-parameters)
4. [The RAG Pipeline Flow](#the-rag-pipeline-flow)
5. [Document Retrieval Strategy](#document-retrieval-strategy)
6. [Reranking Process](#reranking-process)
7. [Claude Context Window Optimization](#claude-context-window-optimization)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Legal Document RAG (Retrieval-Augmented Generation) Server uses a two-stage pipeline to find the most relevant legal documents for a given query:

1. **Vector Similarity Search** - Fast retrieval of candidate documents using OpenAI embeddings
2. **Semantic Reranking** - Precise relevance scoring using Cohere's rerank model

This approach balances **speed** (vector search) with **accuracy** (reranking) while optimizing for **Claude's context window** limitations.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER / CLAUDE                             │
│                                                                   │
│  Request: "Find SAFE agreement templates"                        │
│  top_k: 10 (requested documents)                                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP Server (FastMCP)                           │
│                  legal_rag_server.py                              │
│                                                                   │
│  • Validates request (1 ≤ top_k ≤ 10)                            │
│  • Routes to search pipeline                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   RAG Pipeline Orchestrator                       │
│               search_documents_with_rerank()                      │
│                  legal_rag_utils.py                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│  STAGE 1:        │                    │  Configuration   │
│  Vector Search   │                    │  Loading         │
│                  │                    │                  │
│  • OpenAI        │                    │  • API Keys      │
│    Embeddings    │                    │  • Models        │
│  • Supabase      │                    │  • Thresholds    │
│    pgvector      │                    │                  │
│                  │                    │                  │
│  Retrieves: 15   │                    │                  │
│  candidates      │                    │                  │
└────────┬─────────┘                    └──────────────────┘
         │
         ▼
┌──────────────────┐
│  STAGE 2:        │
│  Reranking       │
│                  │
│  • Cohere        │
│    rerank-v3.5   │
│  • Semantic      │
│    relevance     │
│                  │
│  Returns: Top 5  │
│  (capped)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Response to Claude                             │
│                                                                   │
│  Returns: Up to 5 most relevant documents                        │
│  • Document content                                              │
│  • Metadata                                                      │
│  • Relevance scores                                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Configuration Parameters

### User-Facing Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `query` | string | *required* | 1-1000 chars | Natural language search query |
| `top_k` | integer | 10 | 1-10 | Number of results requested |
| `document_type` | string | `null` | "practice_guide", "agreement", "clause" | Optional document type filter |

### System Configuration (LegalRAGConfig)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `supabase_url` | string | from env | Supabase project URL |
| `supabase_key` | string | from env | Supabase service role key |
| `openai_api_key` | string | from env | OpenAI API key |
| `cohere_api_key` | string | from env | Cohere API key |
| `embedding_model` | string | "text-embedding-3-small" | OpenAI embedding model |
| `rerank_model` | string | "rerank-v3.5" | Cohere rerank model |
| `match_threshold` | float | 0.5 | Minimum similarity for vector search (0.0-1.0) |

### Internal Pipeline Parameters

| Parameter | Value | Location | Purpose |
|-----------|-------|----------|---------|
| `search_count` | **15** | Line 293 (legal_rag_utils.py) | Number of candidates retrieved from vector DB |
| `rerank_top_n` | **min(top_k, 5)** | Line 339 (legal_rag_utils.py) | Maximum documents returned after reranking |

---

## The RAG Pipeline Flow

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Query Validation                                        │
├─────────────────────────────────────────────────────────────────┤
│ Input:  query = "SAFE agreement best practices"                │
│         top_k = 10                                              │
│                                                                 │
│ Action: Validate query length (1-1000 chars)                   │
│         Validate top_k range (1-10)                             │
│                                                                 │
│ Result: ✓ Valid                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Generate Query Embedding                                │
├─────────────────────────────────────────────────────────────────┤
│ Service: OpenAI API                                             │
│ Model:   text-embedding-3-small                                 │
│                                                                 │
│ Input:   "SAFE agreement best practices"                        │
│ Output:  1536-dimensional vector                                │
│          [0.123, -0.456, 0.789, ...]                            │
│                                                                 │
│ Time:    ~200-500ms                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Vector Similarity Search                                │
├─────────────────────────────────────────────────────────────────┤
│ Service:  Supabase (PostgreSQL + pgvector)                      │
│ Function: match_n8n_law_startuplaw()                            │
│                                                                 │
│ Parameters:                                                     │
│   • query_embedding: [vector from Step 2]                       │
│   • match_count: 15 (hardcoded)                                 │
│   • match_threshold: 0.5                                        │
│                                                                 │
│ Process:                                                        │
│   1. Cosine similarity between query and all document vectors   │
│   2. Filter: similarity >= 0.5                                  │
│   3. Sort by similarity score (descending)                      │
│   4. Return top 15 matches                                      │
│                                                                 │
│ Output: 0-15 documents (depends on database content)            │
│         Each with similarity score (0.5-1.0)                    │
│                                                                 │
│ Example Results:                                                │
│   Doc ID  | Title                    | Similarity              │
│   --------|--------------------------|----------               │
│   abc123  | SAFE Agreement Template  | 0.92                    │
│   def456  | YC SAFE Guide           | 0.88                    │
│   ghi789  | Equity Financing Basics | 0.76                    │
│   ...     | ...                     | ...                     │
│   (up to 15 documents)                                          │
│                                                                 │
│ Time: ~100-300ms                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Document Type Filtering (Optional)                      │
├─────────────────────────────────────────────────────────────────┤
│ If document_type is specified:                                  │
│                                                                 │
│ Filter: Keep only documents where                               │
│         metadata.type == document_type                          │
│                                                                 │
│ Example:                                                        │
│   • Input: 15 documents (mixed types)                           │
│   • Filter: document_type = "agreement"                         │
│   • Output: 8 documents (only agreements)                       │
│                                                                 │
│ If not specified: Pass all documents to next stage              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Semantic Reranking                                      │
├─────────────────────────────────────────────────────────────────┤
│ Service: Cohere API                                             │
│ Model:   rerank-v3.5                                            │
│                                                                 │
│ Input:                                                          │
│   • Query: "SAFE agreement best practices"                      │
│   • Documents: [list of 8-15 candidate docs]                   │
│   • top_n: min(10, 5) = 5                                       │
│                                                                 │
│ Process:                                                        │
│   1. Deep semantic analysis of query + each document            │
│   2. Score each document for relevance (0.0-1.0)                │
│   3. Rank by relevance score                                    │
│   4. Return top 5 most relevant                                 │
│                                                                 │
│ Why Reranking?                                                  │
│   • Vector search uses embeddings (fast but approximate)        │
│   • Reranking uses full text analysis (slow but accurate)       │
│   • Best of both: fast retrieval + accurate ranking             │
│                                                                 │
│ Output: Up to 5 documents with relevance_score                  │
│                                                                 │
│ Example:                                                        │
│   Doc ID  | Title                    | Relevance               │
│   --------|--------------------------|----------               │
│   abc123  | SAFE Agreement Template  | 0.98                    │
│   def456  | YC SAFE Guide           | 0.95                    │
│   xyz999  | SAFE Conversion Terms   | 0.87                    │
│   klm111  | SAFE vs Convertible Note| 0.82                    │
│   pqr222  | Post-Money SAFE Explained| 0.79                   │
│                                                                 │
│ Time: ~500-1000ms                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Return Results to Claude                                │
├─────────────────────────────────────────────────────────────────┤
│ Format:                                                         │
│ {                                                               │
│   "query": "SAFE agreement best practices",                     │
│   "document_type": null,                                        │
│   "total_results": 5,                                           │
│   "results": [                                                  │
│     {                                                           │
│       "id": "abc123",                                           │
│       "content": "...",  // Full document text                  │
│       "metadata": {                                             │
│         "title": "SAFE Agreement Template",                     │
│         "type": "agreement",                                    │
│         ...                                                     │
│       },                                                        │
│       "relevance_score": 0.98                                   │
│     },                                                          │
│     ...                                                         │
│   ]                                                             │
│ }                                                               │
│                                                                 │
│ Total Time: ~800-1800ms                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Document Retrieval Strategy

### Why 15 Candidates?

The system retrieves **15 documents** from the vector database before reranking. This number balances:

1. **Diversity** - Gives reranker enough options to choose from
2. **Cost** - Cohere charges per document reranked
3. **Performance** - More documents = longer processing time
4. **Quality** - Too few candidates limits reranker effectiveness

```
┌────────────────────────────────────────────────────────────┐
│         Retrieval Count vs Quality Tradeoff                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  10 candidates  →  Fast, cheap, but may miss good docs    │
│  15 candidates  →  ✓ Balanced (current)                   │
│  30 candidates  →  Expensive, slow, minimal quality gain  │
│  50+ candidates →  Not recommended                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Adaptive Retrieval

The system gracefully handles cases where fewer documents exist:

```python
# Request 15 documents
search_count = 15

# Supabase returns what's available
results = vector_search()  # Could return 0, 5, 10, or 15

# Reranker adapts
if len(results) == 3:
    # Rerank 3 docs, return min(top_k, 3)
elif len(results) == 15:
    # Rerank 15 docs, return min(top_k, 5)
```

**Examples:**

| Database Has | Vector Returns | Reranker Processes | User Receives |
|--------------|----------------|-------------------|---------------|
| 3 documents  | 3 | 3 | min(3, top_k, 5) |
| 10 documents | 10 | 10 | min(10, top_k, 5) = 5 max |
| 100 documents| 15 | 15 | min(15, top_k, 5) = 5 max |

---

## Reranking Process

### Why Rerank?

Vector similarity search is **fast but imperfect**:
- Embeddings capture semantic meaning but lose nuance
- Cosine similarity is a crude measure of relevance
- Context and intent can be misunderstood

Reranking provides **accurate relevance scoring**:
- Analyzes full text, not just embeddings
- Understands query intent deeply
- Considers context and relationships

### Reranking Parameters

```python
top_n = min(top_k, 5)
```

This formula ensures:
1. **User requests 3** → Returns 3 (respects user preference)
2. **User requests 5** → Returns 5 (maximum)
3. **User requests 10** → Returns 5 (capped for Claude)

### Reranking Flow

```
Input: 15 candidate documents + user query
           ↓
┌──────────────────────────────────────┐
│   For each document:                 │
│   1. Analyze query + document text   │
│   2. Score semantic relevance        │
│   3. Assign relevance_score (0-1)    │
└──────────────────────────────────────┘
           ↓
Sort by relevance_score (descending)
           ↓
Select top min(top_k, 5) documents
           ↓
Return with relevance scores
```

### Relevance Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0.90 - 1.00 | Highly relevant, directly answers query |
| 0.75 - 0.89 | Very relevant, contains key information |
| 0.60 - 0.74 | Relevant, related to query topic |
| 0.40 - 0.59 | Somewhat relevant, tangentially related |
| 0.00 - 0.39 | Low relevance, likely not useful |

---

## Claude Context Window Optimization

### The Problem

Claude has a finite context window:
- Claude 3.5 Sonnet: ~200K tokens (~150K words)
- Legal documents: 2-10KB each (500-2500 words)
- **10 documents = 20-100KB = 5-25K words**

Sending too many documents causes:
- ❌ Context overflow errors
- ❌ Degraded response quality
- ❌ Slower processing
- ❌ Higher costs

### The Solution

**Cap reranker output at 5 documents:**

```python
# legal_rag_utils.py, line 339
top_n = min(top_k, 5)  # Never return more than 5
```

This ensures Claude receives:
- **Maximum: 5 documents**
- **~10-50KB of text**
- **~2.5-12.5K words**
- **Well within context limits** ✓

### Estimated Context Usage

| Documents | Avg Size | Total Text | Claude Tokens | % of Context |
|-----------|----------|------------|---------------|--------------|
| 1 doc     | 5KB      | 5KB        | ~1,250        | 0.6%         |
| 3 docs    | 5KB      | 15KB       | ~3,750        | 1.9%         |
| 5 docs    | 5KB      | 25KB       | ~6,250        | 3.1%         |
| 5 docs    | 10KB     | 50KB       | ~12,500       | 6.3%         |

**All well within safe limits!**

### User Experience

Users can request `top_k = 10`, but will receive 5 documents:

```python
# User request
response = semantic_search_legal_documents(
    query="SAFE agreement",
    top_k=10  # Request 10
)

# Actual response
{
    "total_results": 5,  # Received 5 (capped)
    "results": [...]     # 5 most relevant docs
}
```

**Documentation makes this clear:**
> "System returns up to 5 documents to optimize for Claude's context window."

---

## Usage Examples

### Example 1: Basic Search

```python
# Request default (10 documents requested, 5 returned)
response = semantic_search_legal_documents(
    query="How do I incorporate a Delaware C-corp?"
)

# Response
{
    "query": "How do I incorporate a Delaware C-corp?",
    "document_type": null,
    "total_results": 5,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Delaware C-Corp Incorporation Guide...",
            "metadata": {
                "title": "Delaware C-Corp Formation Checklist",
                "type": "practice_guide"
            },
            "relevance_score": 0.96
        },
        // ... 4 more documents
    ]
}
```

### Example 2: Request Fewer Documents

```python
# User wants only top 3 results
response = semantic_search_legal_documents(
    query="Employee stock option plans",
    top_k=3  # Request 3
)

# Response
{
    "total_results": 3,  # Received 3 (as requested)
    "results": [...]     # 3 documents
}
```

### Example 3: With Document Type Filter

```python
# Search only agreements
response = semantic_search_legal_documents(
    query="Non-disclosure agreement",
    top_k=5,
    document_type="agreement"  # Filter
)

# Response includes only documents where metadata.type == "agreement"
```

### Example 4: Edge Case - Few Documents Available

```python
# Query with limited matches
response = semantic_search_legal_documents(
    query="Very specific niche legal topic",
    top_k=10
)

# Response
{
    "total_results": 2,  # Only 2 documents matched
    "results": [...]     # 2 documents (all available)
}
```

---

## Troubleshooting

### Issue: No Results Returned

**Symptoms:**
```json
{
    "total_results": 0,
    "results": [],
    "message": "No documents found matching your query"
}
```

**Possible Causes:**
1. Query too specific or uses jargon not in documents
2. Match threshold (0.5) filters out all results
3. Document type filter too restrictive
4. Database is empty or has limited content

**Solutions:**
- Broaden query terms
- Try without document_type filter
- Lower match_threshold in config (0.5 → 0.3)
- Verify database has documents

### Issue: Results Not Relevant

**Symptoms:**
- Documents returned but don't match query intent
- Low relevance scores (< 0.6)

**Possible Causes:**
1. Vector embeddings don't capture query nuance
2. Reranker needs better context
3. Document metadata incorrect

**Solutions:**
- Rephrase query with more context
- Try adding document_type filter
- Check document metadata quality

### Issue: Slow Response Times

**Symptoms:**
- Requests taking > 3 seconds

**Possible Causes:**
1. Supabase vector search slow (large database)
2. Cohere reranking API latency
3. Network issues

**Solutions:**
- Check Supabase logs/performance
- Verify Cohere API status
- Consider reducing search_count if needed

### Issue: Context Window Errors (Should Not Happen)

**Symptoms:**
- Claude refuses to process results
- "Context too long" errors

**Verification:**
```python
# Check: Should never happen with current setup
assert total_results <= 5, "Reranker cap failed!"
```

**Solution:**
- This should not occur with `top_n = min(top_k, 5)` in place
- If it does, verify legal_rag_utils.py line 339
- Check that document sizes are reasonable (< 50KB each)

---

## Performance Metrics

### Expected Latencies

| Stage | Average Time | Description |
|-------|--------------|-------------|
| Validation | 1-5ms | Query validation and parsing |
| Embedding Generation | 200-500ms | OpenAI API call |
| Vector Search | 100-300ms | Supabase pgvector query |
| Filtering | 1-10ms | Document type filtering |
| Reranking | 500-1000ms | Cohere API call |
| **Total** | **800-1800ms** | End-to-end request |

### Cost Analysis (per request)

| Component | Cost | Notes |
|-----------|------|-------|
| OpenAI Embedding | $0.00002 | text-embedding-3-small |
| Cohere Reranking | $0.00015-$0.00030 | Based on 15 docs @ $0.00002/doc |
| Supabase Vector Search | ~$0.00001 | Database query cost |
| **Total per request** | **~$0.00033** | Very cost-effective! |

### Scalability

Current configuration supports:
- **Concurrent requests:** 100+ (depends on API rate limits)
- **Database size:** Millions of documents (pgvector scales well)
- **Response time:** Consistent regardless of DB size

---

## Configuration Tuning

### When to Adjust Parameters

| Parameter | Current | Increase If... | Decrease If... |
|-----------|---------|----------------|----------------|
| `search_count` | 15 | Need more reranking diversity | Cohere costs too high |
| `rerank_top_n` cap | 5 | Claude context is underutilized | Context overflow occurs |
| `match_threshold` | 0.5 | Too many irrelevant results | Missing relevant documents |
| `top_k` max | 10 | Users need more flexibility | Want to enforce strict limits |

### Recommended Configurations

**Conservative (Current):**
```python
search_count = 15
rerank_top_n = min(top_k, 5)
match_threshold = 0.5
```

**Cost-Optimized:**
```python
search_count = 10  # Fewer docs to rerank
rerank_top_n = min(top_k, 3)  # Return fewer
match_threshold = 0.6  # Higher quality filter
```

**Quality-Optimized:**
```python
search_count = 20  # More candidates
rerank_top_n = min(top_k, 5)
match_threshold = 0.4  # Cast wider net
```

---

## Summary

### Key Takeaways

1. ✅ **Two-stage pipeline:** Fast vector search + accurate reranking
2. ✅ **Retrieves 15 candidates,** returns up to 5 results
3. ✅ **Optimized for Claude** context window (5 docs max)
4. ✅ **User requests top_k (1-10),** system returns min(top_k, 5)
5. ✅ **Gracefully handles** edge cases (few docs, no matches)
6. ✅ **Cost-effective:** ~$0.0003 per request
7. ✅ **Fast:** 800-1800ms end-to-end

### Request Flow Summary

```
User: top_k = 10
  → Vector: Retrieve 15 candidates
    → Rerank: Process 15, return top 5
      → Claude: Receives 5 documents ✓

User: top_k = 3
  → Vector: Retrieve 15 candidates
    → Rerank: Process 15, return top 3
      → Claude: Receives 3 documents ✓

Database: Only 2 docs match
  → Vector: Retrieve 2 candidates
    → Rerank: Process 2, return 2
      → Claude: Receives 2 documents ✓
```

---

## Changelog

### Version 1.0 (Current)
- Initial configuration: 15 → 5 pipeline
- top_k range: 1-10
- Default top_k: 10
- Reranker cap: 5 documents
- Match threshold: 0.5

---

## References

- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings
- **Cohere Rerank:** https://docs.cohere.com/docs/reranking
- **Supabase pgvector:** https://supabase.com/docs/guides/database/extensions/pgvector
- **FastMCP Documentation:** https://github.com/jlowin/fastmcp

---

*Last Updated: December 10, 2025*
*Maintained by: Legal RAG Server Team*

