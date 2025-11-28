#!/usr/bin/env python3
"""
Direct database query to check actual similarity scores for baseline query.
This bypasses the API to see raw database results.
"""
import asyncio
import os
from packages.ingestion.embedder import create_embedder
from packages.utils.supabase_client import SupabaseRestClient

async def main():
    # Initialize
    embedder = create_embedder()
    client = SupabaseRestClient()
    await client.initialize()

    # Baseline query
    query = "C'est quoi un chantier de type D ?"
    print(f"Query: {query}\n")

    # Generate embedding
    embedding = await embedder.embed_query(query)
    print(f"Embedding generated: {len(embedding)} dimensions\n")

    # Test different thresholds
    thresholds = [0.0, 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]

    print("="*80)
    print("SIMILARITY SCORE ANALYSIS")
    print("="*80)
    print(f"{'Threshold':<12} {'Results':<10} {'Max Sim':<10} {'Avg Sim':<10} {'Min Sim':<10}")
    print("-"*80)

    for threshold in thresholds:
        results = await client.similarity_search(
            query_embedding=embedding,
            limit=10,
            similarity_threshold=threshold
        )

        if results:
            similarities = [r.get('similarity', 0) for r in results]
            max_sim = max(similarities)
            avg_sim = sum(similarities) / len(similarities)
            min_sim = min(similarities)
            print(f"{threshold:<12.2f} {len(results):<10} {max_sim:<10.3f} {avg_sim:<10.3f} {min_sim:<10.3f}")
        else:
            print(f"{threshold:<12.2f} {0:<10} {'-':<10} {'-':<10} {'-':<10}")

    print("\n" + "="*80)
    print("TOP 5 RESULTS AT THRESHOLD 0.0 (show all):")
    print("="*80)

    # Get top results with no threshold
    results = await client.similarity_search(
        query_embedding=embedding,
        limit=5,
        similarity_threshold=0.0
    )

    for i, result in enumerate(results, 1):
        similarity = result.get('similarity', 0)
        title = result.get('document_title', 'Unknown')[:60]
        content = result.get('content', '')[:100].replace('\n', ' ')
        print(f"\n[{i}] Similarity: {similarity:.4f}")
        print(f"    Title: {title}")
        print(f"    Content: {content}...")

if __name__ == "__main__":
    asyncio.run(main())
