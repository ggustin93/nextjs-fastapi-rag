"""Benchmark: Vector-only vs Hybrid Search.

Compares retrieval quality on golden dataset to determine
if hybrid search (Vector + FTS + RRF) outperforms pure vector search.

Usage:
    .venv/bin/python tests/benchmark_search.py
"""

import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.config import settings
from packages.ingestion.embedder import EmbeddingGenerator
from packages.utils.supabase_client import SupabaseRestClient


@dataclass
class BenchmarkResult:
    query: str
    query_type: str
    expected_keywords: list[str]
    min_similarity: float
    # Vector-only results
    vector_top_similarity: float
    vector_keyword_hits: int
    vector_keyword_total: int
    # Hybrid results
    hybrid_top_similarity: float
    hybrid_keyword_hits: int
    hybrid_keyword_total: int


async def run_benchmark():
    """Run search benchmark comparing vector vs hybrid."""
    # Load golden dataset
    golden_path = Path(__file__).parent / "golden_dataset.csv"
    queries = []
    with open(golden_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(row)

    print(f"📊 Loaded {len(queries)} test queries from golden dataset\n")

    # Initialize clients
    embedder = EmbeddingGenerator()
    db_client = SupabaseRestClient()
    await db_client.initialize()

    results: list[BenchmarkResult] = []

    print("Running benchmark...\n")
    print("-" * 80)

    for i, q in enumerate(queries, 1):
        query = q["query"]
        expected_keywords = json.loads(q["expected_keywords"].replace("'", '"'))
        min_sim = float(q["min_similarity"])
        query_type = q["query_type"]

        # Generate embedding
        embedding = await embedder.embed_query(query)

        # 1. Vector-only search
        vector_results = await db_client.similarity_search(
            query_embedding=embedding,
            limit=5,
            similarity_threshold=0.2,
        )

        # 2. Hybrid search (Vector + FTS + RRF)
        hybrid_results = await db_client.hybrid_search(
            query_text=query,
            query_embedding=embedding,
            limit=5,
            similarity_threshold=0.2,
            exclude_toc=True,
            rrf_k=settings.search.rrf_k,
        )

        # Calculate metrics
        def count_keyword_hits(search_results, keywords):
            hits = 0
            all_content = " ".join(
                r.get("content", "").lower() + " " + r.get("document_title", "").lower()
                for r in search_results
            )
            for kw in keywords:
                if kw.lower() in all_content:
                    hits += 1
            return hits

        vector_sim = vector_results[0]["similarity"] if vector_results else 0
        hybrid_sim = hybrid_results[0]["similarity"] if hybrid_results else 0
        vector_hits = count_keyword_hits(vector_results, expected_keywords)
        hybrid_hits = count_keyword_hits(hybrid_results, expected_keywords)

        result = BenchmarkResult(
            query=query,
            query_type=query_type,
            expected_keywords=expected_keywords,
            min_similarity=min_sim,
            vector_top_similarity=vector_sim,
            vector_keyword_hits=vector_hits,
            vector_keyword_total=len(expected_keywords),
            hybrid_top_similarity=hybrid_sim,
            hybrid_keyword_hits=hybrid_hits,
            hybrid_keyword_total=len(expected_keywords),
        )
        results.append(result)

        # Print progress
        winner = "🟢 HYBRID" if hybrid_hits >= vector_hits else "🔵 VECTOR"
        if hybrid_hits == vector_hits:
            winner = "🟡 TIE"

        print(f"[{i:2d}] {query[:50]:<50}")
        print(f"     Vector: sim={vector_sim:.3f} keywords={vector_hits}/{len(expected_keywords)}")
        print(f"     Hybrid: sim={hybrid_sim:.3f} keywords={hybrid_hits}/{len(expected_keywords)}")
        print(f"     Winner: {winner}")
        print()

    print("-" * 80)
    print("\n📈 SUMMARY\n")

    # Aggregate by query type
    by_type: dict[str, list[BenchmarkResult]] = {}
    for r in results:
        by_type.setdefault(r.query_type, []).append(r)

    print(f"{'Query Type':<15} {'Vector Hits':<12} {'Hybrid Hits':<12} {'Winner':<10}")
    print("-" * 50)

    total_vector_wins = 0
    total_hybrid_wins = 0
    total_ties = 0

    for qtype, type_results in sorted(by_type.items()):
        v_hits = sum(r.vector_keyword_hits for r in type_results)
        h_hits = sum(r.hybrid_keyword_hits for r in type_results)
        v_total = sum(r.vector_keyword_total for r in type_results)
        h_total = sum(r.hybrid_keyword_total for r in type_results)

        if h_hits > v_hits:
            winner = "HYBRID"
            total_hybrid_wins += 1
        elif v_hits > h_hits:
            winner = "VECTOR"
            total_vector_wins += 1
        else:
            winner = "TIE"
            total_ties += 1

        print(f"{qtype:<15} {v_hits}/{v_total:<10} {h_hits}/{h_total:<10} {winner:<10}")

    print("-" * 50)

    # Overall winner
    total_v = sum(r.vector_keyword_hits for r in results)
    total_h = sum(r.hybrid_keyword_hits for r in results)
    total_kw = sum(r.vector_keyword_total for r in results)

    print(f"\n{'TOTAL':<15} {total_v}/{total_kw:<10} {total_h}/{total_kw:<10}")

    avg_v_sim = sum(r.vector_top_similarity for r in results) / len(results)
    avg_h_sim = sum(r.hybrid_top_similarity for r in results) / len(results)

    print(f"\nAvg Similarity:  Vector={avg_v_sim:.3f}  Hybrid={avg_h_sim:.3f}")

    print("\n" + "=" * 50)
    if total_h > total_v:
        print("🏆 WINNER: HYBRID SEARCH")
        print(f"   Hybrid found {total_h - total_v} more keyword matches ({(total_h/total_kw)*100:.1f}% vs {(total_v/total_kw)*100:.1f}%)")
    elif total_v > total_h:
        print("🏆 WINNER: VECTOR SEARCH")
        print(f"   Vector found {total_v - total_h} more keyword matches ({(total_v/total_kw)*100:.1f}% vs {(total_h/total_kw)*100:.1f}%)")
    else:
        print("🏆 TIE - Both approaches perform equally")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
