#!/usr/bin/env python3
"""
RAG System Evaluation Script
Measures: Recall@5, MRR, Precision, Latency
"""
import asyncio
import csv
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
import httpx

# Configuration
API_URL = "http://localhost:8000/api/v1/chat/stream"
TEST_DATA = Path("tests/golden_dataset.csv")
RESULTS_DIR = Path("tests/results")
RESULTS_DIR.mkdir(exist_ok=True)

class RAGEvaluator:
    def __init__(self):
        self.results = []
        self.metrics = {
            "recall_at_5": [],
            "mrr": [],
            "precision_at_5": [],
            "latencies": [],
            "similarity_scores": []
        }

    async def query_rag(self, query: str) -> Tuple[List[Dict], float, str]:
        """Query RAG system and return sources, latency, response."""
        start_time = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                API_URL,
                json={"message": query},
                headers={"Content-Type": "application/json"}
            )

        latency = (time.time() - start_time) * 1000  # ms

        if response.status_code != 200:
            return [], latency, f"ERROR: {response.status_code}"

        # Parse SSE response to extract sources
        # SSE format: "event: <type>\ndata: <json>\n\n"
        sources = []
        response_text = ""
        current_event = None

        for line in response.text.split('\n'):
            line = line.strip()
            if line.startswith('event:'):
                current_event = line[6:].strip()
            elif line.startswith('data:'):
                try:
                    data = json.loads(line[5:].strip())
                    if current_event == 'sources':
                        sources = data.get('sources', [])
                    elif current_event in ('chunk', 'token'):
                        response_text += data.get('content', '')
                except json.JSONDecodeError:
                    continue

        return sources, latency, response_text

    def calculate_recall(self, sources: List[Dict], expected_keywords: List[str], response_text: str = "") -> float:
        """Calculate recall: fraction of expected keywords found in response text.

        Since sources don't include chunk content, we check if keywords appear in
        the LLM response text, which is generated from retrieved chunks.
        This is a practical measure of end-to-end retrieval quality.
        """
        if not expected_keywords:
            return 1.0

        # Check keywords in response text (reflects retrieval quality)
        response_lower = response_text.lower()

        found = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return found / len(expected_keywords)

    def calculate_mrr(self, sources: List[Dict], expected_doc_patterns: List[str] = None) -> float:
        """Calculate Mean Reciprocal Rank based on document relevance.

        Uses document title/path to determine relevance since source content
        is not included in API response.
        """
        if not sources:
            return 0.0

        # Expected patterns for relevant documents (type D related)
        relevant_patterns = expected_doc_patterns or [
            "type d", "type_d", "occupation", "osiris", "userguide"
        ]

        for rank, source in enumerate(sources[:5], start=1):
            title = source.get('title', '').lower()
            path = source.get('path', '').lower()
            combined = f"{title} {path}"

            # Check if source is from a relevant document
            if any(pattern in combined for pattern in relevant_patterns):
                return 1.0 / rank

        return 0.0  # No relevant result in top 5

    def calculate_precision(self, sources: List[Dict], expected_doc_patterns: List[str] = None) -> float:
        """Calculate precision@5: fraction of top 5 sources from relevant documents.

        Uses document title/path to determine relevance since source content
        is not included in API response.
        """
        if not sources:
            return 0.0

        # Expected patterns for relevant documents
        relevant_patterns = expected_doc_patterns or [
            "type d", "type_d", "occupation", "osiris", "userguide"
        ]

        relevant_count = 0
        for source in sources[:5]:
            title = source.get('title', '').lower()
            path = source.get('path', '').lower()
            combined = f"{title} {path}"

            if any(pattern in combined for pattern in relevant_patterns):
                relevant_count += 1

        return relevant_count / min(5, len(sources))

    def extract_similarity_scores(self, sources: List[Dict]) -> List[float]:
        """Extract similarity scores from sources."""
        return [s.get('similarity', 0.0) for s in sources[:5]]

    async def evaluate_query(self, row: Dict) -> Dict:
        """Evaluate a single query."""
        query = row['query']
        expected_keywords = json.loads(row['expected_keywords'].replace("'", '"'))
        min_similarity = float(row['min_similarity'])
        query_type = row['query_type']

        print(f"\n🔍 Testing: {query}")
        print(f"   Type: {query_type} | Min Similarity: {min_similarity}")

        # Query RAG system
        sources, latency, response = await self.query_rag(query)

        # Calculate metrics
        # Recall: check if keywords appear in response text (reflects retrieval quality)
        recall = self.calculate_recall(sources, expected_keywords, response)
        # MRR/Precision: use document patterns since we don't have chunk content
        mrr = self.calculate_mrr(sources)
        precision = self.calculate_precision(sources)
        similarity_scores = self.extract_similarity_scores(sources)

        # Check if similarity threshold met
        meets_threshold = all(s >= min_similarity for s in similarity_scores if s > 0)

        result = {
            "query": query,
            "query_type": query_type,
            "recall": recall,
            "mrr": mrr,
            "precision": precision,
            "latency_ms": latency,
            "similarity_scores": similarity_scores,
            "meets_threshold": meets_threshold,
            "num_sources": len(sources),
            "response_length": len(response)
        }

        # Print result
        status = "✅" if recall >= 0.6 and meets_threshold else "❌"
        print(f"   {status} Recall: {recall:.2f} | MRR: {mrr:.2f} | Precision: {precision:.2f}")
        print(f"   Latency: {latency:.0f}ms | Sources: {len(sources)} | Similarities: {similarity_scores[:3]}")

        return result

    async def run_evaluation(self):
        """Run full evaluation on test dataset."""
        print("=" * 80)
        print("🚀 RAG SYSTEM EVALUATION")
        print("=" * 80)

        # Load test data
        with open(TEST_DATA, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            test_cases = list(reader)

        print(f"\n📊 Test Dataset: {len(test_cases)} queries")

        # Evaluate each query
        for row in test_cases:
            result = await self.evaluate_query(row)
            self.results.append(result)

            # Update metrics
            self.metrics["recall_at_5"].append(result["recall"])
            self.metrics["mrr"].append(result["mrr"])
            self.metrics["precision_at_5"].append(result["precision"])
            self.metrics["latencies"].append(result["latency_ms"])
            self.metrics["similarity_scores"].extend(result["similarity_scores"])

        # Calculate aggregate metrics
        self.print_summary()
        self.save_results()

    def print_summary(self):
        """Print evaluation summary."""
        print("\n" + "=" * 80)
        print("📈 EVALUATION SUMMARY")
        print("=" * 80)

        # Overall metrics
        avg_recall = sum(self.metrics["recall_at_5"]) / len(self.metrics["recall_at_5"])
        avg_mrr = sum(self.metrics["mrr"]) / len(self.metrics["mrr"])
        avg_precision = sum(self.metrics["precision_at_5"]) / len(self.metrics["precision_at_5"])

        latencies = self.metrics["latencies"]
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

        similarities = [s for s in self.metrics["similarity_scores"] if s > 0]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        print(f"\n🎯 PRIMARY METRICS:")
        print(f"   Recall@5:     {avg_recall:.2%} (Target: >60%)")
        print(f"   MRR:          {avg_mrr:.3f} (Target: >0.45)")
        print(f"   Precision@5:  {avg_precision:.2%} (Target: >70%)")

        print(f"\n⚡ PERFORMANCE:")
        print(f"   Avg Latency:  {avg_latency:.0f}ms")
        print(f"   P95 Latency:  {p95_latency:.0f}ms (Target: <600ms)")

        print(f"\n📊 RETRIEVAL QUALITY:")
        print(f"   Avg Similarity: {avg_similarity:.3f} (Target: >0.65)")
        print(f"   Queries with results: {sum(1 for r in self.results if r['num_sources'] > 0)}/{len(self.results)}")

        # By query type
        print(f"\n📋 BY QUERY TYPE:")
        query_types = set(r["query_type"] for r in self.results)
        for qtype in sorted(query_types):
            type_results = [r for r in self.results if r["query_type"] == qtype]
            type_recall = sum(r["recall"] for r in type_results) / len(type_results)
            print(f"   {qtype:15s}: Recall {type_recall:.2%} ({len(type_results)} queries)")

        # Pass/Fail
        pass_count = sum(1 for r in self.results if r["recall"] >= 0.6 and r["meets_threshold"])
        print(f"\n✅ PASSED: {pass_count}/{len(self.results)} ({pass_count/len(self.results):.1%})")
        print("=" * 80)

    def save_results(self):
        """Save detailed results to JSON."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = RESULTS_DIR / f"evaluation_{timestamp}.json"

        summary = {
            "timestamp": timestamp,
            "test_count": len(self.results),
            "metrics": {
                "recall_at_5": sum(self.metrics["recall_at_5"]) / len(self.metrics["recall_at_5"]),
                "mrr": sum(self.metrics["mrr"]) / len(self.metrics["mrr"]),
                "precision_at_5": sum(self.metrics["precision_at_5"]) / len(self.metrics["precision_at_5"]),
                "avg_latency_ms": sum(self.metrics["latencies"]) / len(self.metrics["latencies"]),
                "p95_latency_ms": sorted(self.metrics["latencies"])[int(0.95 * len(self.metrics["latencies"]))],
                "avg_similarity": sum([s for s in self.metrics["similarity_scores"] if s > 0]) / len([s for s in self.metrics["similarity_scores"] if s > 0]) if [s for s in self.metrics["similarity_scores"] if s > 0] else 0
            },
            "detailed_results": self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results saved to: {output_file}")

async def main():
    evaluator = RAGEvaluator()
    await evaluator.run_evaluation()

if __name__ == "__main__":
    asyncio.run(main())
