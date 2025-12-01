# Troubleshooting Guide

## Session: RAG Retrieval Quality Issues

**Date**: 28 November 2025

---

## Problem Description

### Symptoms

When asking the RAG chatbot **"C'est quoi un chantier de type D?"** (What is a type D construction site?), the system returned **vague, unhelpful responses** that didn't include the actual definition from the knowledge base.

### Expected Behavior

The system should retrieve and cite the actual definition chunk:

- **D - Dispense** (Type D - Exemption)
- Superficie inférieure à 50 m²
- Durée d'exécution inférieure à 24 heures (1 jour ouvrable)

### Actual Behavior

The system returned generic information without the specific criteria, citing irrelevant chunks like table of contents entries.

---

## Root Cause Analysis

### 1. Semantic Similarity Mismatch

The chunks containing the actual TYPE D definition had **LOW semantic similarity scores** (0.36-0.44), while Table of Contents (TOC) chunks that merely *mention* "chantier de type D" had **HIGH similarity scores** (0.71-0.82).

**Why?** The definition chunk says:

```text
D - Dispense * Superficie inférieure à 50m² * Durée inférieure à 24 heures
```

This text doesn't contain the words "chantier de type D" - it uses "D - Dispense" as a header. Vector embeddings measure semantic closeness to the query terms, so "chantier de type D" is more similar to a TOC entry that literally contains those words than to a definition that explains what Type D means.

### 2. Similarity Threshold Filtering

With `SEARCH_SIMILARITY_THRESHOLD=0.45`, chunks with similarity below 45% were filtered out. This excluded the actual definition chunks (0.36-0.44) while keeping useless TOC chunks (0.71-0.82).

### 3. FlashRank Reranker Failure

The FlashRank cross-encoder reranker gave **0.0 scores** to definition chunks because:

- Cross-encoders optimize for query-document term overlap
- The definition chunk doesn't contain query terms like "chantier", "type", "D"
- TOC chunks that mention these terms were ranked higher

### 4. Query Reformulation Losing Context

The `reformulate_query` LLM call transformed:

```text
"C'est quoi un chantier de type D?" → "chantier de type d"
```

This lost the **definition-seeking intent** ("C'est quoi" = "What is"). The system couldn't understand the user was asking for a definition.

---

## Solution Implemented

### Code Changes (Complete Removal)

Based on this analysis, reranking and query reformulation code was **completely removed** from the codebase (not just disabled via config). The simplified pipeline now relies on:

1. **Hybrid search with RRF** - Combines vector similarity and French full-text search
2. **PostgreSQL-level filtering** - TOC exclusion and similarity threshold
3. **Original query preservation** - User's query used directly, no reformulation

### Current Configuration

```env
# Search Configuration
SEARCH_SIMILARITY_THRESHOLD=0.25    # Lowered from 0.45 to capture definition chunks
SEARCH_DEFAULT_LIMIT=30             # Balanced chunk retrieval
RRF_K=50                            # RRF ranking parameter
EXCLUDE_TOC=true                    # Filter out TOC chunks at database level
```

### Why This Works

1. **Removing reranking** allows the raw hybrid search results (sorted by RRF fusion) to surface the correct chunks. RRF combines vector similarity AND keyword matching, so it can find chunks that mention related terms even if vector similarity is lower.

2. **Removing reformulation** preserves the original question context, allowing the LLM to understand the user is seeking a definition.

3. **Lowering the threshold** ensures more chunks pass the filter, giving the LLM more context to work with.

4. **TOC exclusion at database level** is more efficient and reliable than post-processing filtering.

---

## Verification

After applying the fix, the curl test returned:

```bash
curl -s -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "C'\''est quoi un chantier de type D ?"}'
```

**Response:**

```text
Un chantier de type D est caractérisé par une emprise inférieure à 50 m²
et une durée d'exécution limitée à 1 jour ouvrable...
```

✅ The correct definition with specific criteria is now being retrieved and cited.

---

## Lessons Learned

### 1. Semantic Search Limitations

Vector embeddings don't capture **definition relationships**. A chunk that *defines* something may have low similarity to a query *asking* for that definition if they don't share vocabulary.

### 2. Reranking Can Hurt

Cross-encoder rerankers (like FlashRank) optimize for term overlap. For definition queries where the answer uses different vocabulary than the question, reranking can actually **deprioritize** the best chunks.

### 3. Query Reformulation Trade-offs

LLM-based query reformulation can lose context. For simple queries or when users phrase things naturally, the original query may work better.

### 4. Test with Real User Queries

Automated similarity metrics don't capture real-world query patterns. Test with actual user questions to find retrieval edge cases.

---

## Recommended Configuration

For **French technical documentation** (tested and optimized):

```env
# Simplified pipeline - reranking/reformulation removed from codebase
SEARCH_SIMILARITY_THRESHOLD=0.25    # Captures definition chunks
SEARCH_DEFAULT_LIMIT=30             # Balanced retrieval
RRF_K=50                            # Standard RRF weighting
EXCLUDE_TOC=true                    # Filter TOC at database level
MAX_CHUNKS_PER_DOCUMENT=5           # Allow more context per source
```

---

## Related Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_SIMILARITY_THRESHOLD` | 0.25 | Minimum vector similarity (0.0-1.0) |
| `SEARCH_DEFAULT_LIMIT` | 30 | Max chunks from hybrid search |
| `MAX_CHUNKS_PER_DOCUMENT` | 5 | Limit chunks per source document |
| `RRF_K` | 50 | RRF ranking parameter (lower = favor top results) |
| `EXCLUDE_TOC` | true | Filter out TOC chunks at database level |

> **Note:** Reranking and query reformulation were **removed** from the codebase after testing showed they hurt accuracy for French technical content. The hybrid search with RRF provides good ranking without these features.

---

## Debug Commands

### Check chunk retrieval scores

```bash
# Tail backend logs for retrieval details
tail -f logs/backend.log 2>/dev/null | grep -E "(similarity|chunks|rerank)"
```

### Test specific query

```bash
curl -s -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "YOUR QUERY HERE"}' | jq -r '.sources[]?.title // .token // .'
```

### Analyze similarity distribution

```python
# Run in Python to check what similarity scores your chunks have
import asyncio
from packages.utils.supabase_client import supabase_client

async def analyze():
    results = await supabase_client.hybrid_search(
        query="your query here",
        embedding=[...],  # Generate with embedder
        limit=50
    )
    for r in results:
        print(f"{r['similarity']:.2f} - {r['title'][:60]}")

asyncio.run(analyze())
```

---

## Contact

For questions about this troubleshooting session, refer to the git history or conversation logs from 28 November 2025.
