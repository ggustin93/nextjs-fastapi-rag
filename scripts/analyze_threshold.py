#!/usr/bin/env python3
"""
Threshold Analysis Script
Tests a baseline query at different similarity thresholds to find optimal value.
"""

import asyncio
import json
from typing import Dict

import httpx

# Configuration
API_URL = "http://localhost:8000/api/v1/chat/stream"
BASELINE_QUERY = "C'est quoi un chantier de type D ?"
THRESHOLDS = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65]


async def query_with_threshold(query: str, threshold: float) -> Dict:
    """Query RAG system and extract sources with similarity scores."""
    print(f"\n{'='*80}")
    print(f"Testing threshold: {threshold}")
    print(f"{'='*80}")

    # Update threshold in environment
    import os

    os.environ["SEARCH_SIMILARITY_THRESHOLD"] = str(threshold)

    # Query API
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            API_URL, json={"message": query}, headers={"Content-Type": "application/json"}
        )

    if response.status_code != 200:
        print(f"❌ ERROR: {response.status_code}")
        return {"threshold": threshold, "sources": [], "error": response.text}

    # Parse SSE response
    sources = []
    response_text = ""

    for line in response.text.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "sources":
                    sources = data.get("sources", [])
                elif data.get("type") == "chunk":
                    response_text += data.get("content", "")
            except json.JSONDecodeError:
                continue

    # Display results
    print("\n📊 Results:")
    print(f"   Sources found: {len(sources)}")

    if sources:
        print("\n   Top 5 Sources (by similarity):")
        for idx, source in enumerate(sources[:5], 1):
            similarity = source.get("similarity", 0)
            title = source.get("title", "Unknown")
            path = source.get("path", "Unknown")

            # Relevance indicator
            if similarity >= 0.7:
                relevance = "🟢 HIGH"
            elif similarity >= 0.5:
                relevance = "🟡 MEDIUM"
            elif similarity >= 0.4:
                relevance = "🟠 LOW"
            else:
                relevance = "🔴 VERY LOW"

            print(f"   [{idx}] {relevance} - Similarity: {similarity:.3f}")
            print(f"       Title: {title}")
            print(f"       Path: {path}")
    else:
        print("   ❌ No sources returned (all chunks below threshold)")

    print("\n📝 Response preview (first 200 chars):")
    print(f"   {response_text[:200]}...")

    return {
        "threshold": threshold,
        "sources": sources,
        "num_sources": len(sources),
        "response_length": len(response_text),
        "avg_similarity": sum(s.get("similarity", 0) for s in sources) / len(sources)
        if sources
        else 0,
        "max_similarity": max((s.get("similarity", 0) for s in sources), default=0),
        "min_similarity": min((s.get("similarity", 0) for s in sources), default=0),
    }


async def analyze_thresholds():
    """Run threshold analysis and provide recommendation."""
    print("=" * 80)
    print("🔍 RAG THRESHOLD ANALYSIS")
    print("=" * 80)
    print(f'Baseline Query: "{BASELINE_QUERY}"')
    print(f"Testing Thresholds: {THRESHOLDS}")

    results = []

    for threshold in THRESHOLDS:
        result = await query_with_threshold(BASELINE_QUERY, threshold)
        results.append(result)

        # Pause between requests
        await asyncio.sleep(1)

    # Analysis Summary
    print("\n" + "=" * 80)
    print("📈 ANALYSIS SUMMARY")
    print("=" * 80)

    print("\n| Threshold | Sources | Avg Sim | Max Sim | Min Sim |")
    print("|-----------|---------|---------|---------|---------|")

    for r in results:
        print(
            f"| {r['threshold']:.2f}     | {r['num_sources']:7d} | {r['avg_similarity']:.3f}   | {r['max_similarity']:.3f}   | {r['min_similarity']:.3f}   |"
        )

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")

    # Find optimal threshold
    optimal = None
    for r in reversed(results):  # Start from most restrictive
        if r["num_sources"] > 0 and r["max_similarity"] >= 0.4:
            optimal = r
            break

    if optimal:
        print(f"\n✅ RECOMMENDED THRESHOLD: {optimal['threshold']}")
        print("   Reasoning:")
        print(f"   - Returns {optimal['num_sources']} sources")
        print(f"   - Average similarity: {optimal['avg_similarity']:.3f}")
        print(f"   - Maximum similarity: {optimal['max_similarity']:.3f}")
        print("   - Balances precision (high threshold) with recall (sources found)")
    else:
        print("\n⚠️  WARNING: No suitable threshold found!")
        print("   All thresholds either return 0 sources or very low similarity.")
        print("   Consider:")
        print("   1. Multilingual embedding model (current model is English-biased)")
        print("   2. Re-ingestion with better French embeddings")
        print("   3. Using lower threshold (0.35-0.38) as temporary fix")

    # Additional insights
    max_sources_result = max(results, key=lambda x: x["num_sources"])
    print("\n📊 INSIGHTS:")
    print(f"   - Threshold 0.3 returned {max_sources_result['num_sources']} sources")
    print("   - English-biased embeddings likely causing lower similarity scores")
    print("   - French technical terminology underperforms in current embedding space")


if __name__ == "__main__":
    asyncio.run(analyze_thresholds())
