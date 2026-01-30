-- Migration: Add ef_search parameter to hybrid_search function
-- This allows query-time tuning of HNSW recall vs latency tradeoff
-- Run after 001_hnsw_index.sql

BEGIN;

-- Replace hybrid_search function with ef_search support
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text text,
  query_embedding vector(1536),
  match_count int DEFAULT 20,
  similarity_threshold float DEFAULT 0.0,
  rrf_k int DEFAULT 60,
  exclude_toc boolean DEFAULT TRUE,
  max_per_doc int DEFAULT 3,
  ef_search int DEFAULT 100
)
RETURNS TABLE (
  chunk_id uuid,
  document_id uuid,
  content text,
  similarity float,
  metadata jsonb,
  document_title text,
  document_source text,
  document_metadata jsonb,
  score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Set HNSW ef_search for this query (higher = better recall, slower)
  PERFORM set_hnsw_ef_search(ef_search);

  RETURN QUERY
  WITH full_text AS (
    SELECT c.id,
           c.document_id as doc_id,
           ROW_NUMBER() OVER(ORDER BY ts_rank_cd(to_tsvector('french', c.content), websearch_to_tsquery('french', query_text)) DESC) as rank
    FROM chunks c
    WHERE to_tsvector('french', c.content) @@ websearch_to_tsquery('french', query_text)
      AND (NOT exclude_toc OR COALESCE(c.is_toc, FALSE) = FALSE)
    LIMIT match_count * 3
  ),
  semantic AS (
    SELECT c.id,
           c.document_id as doc_id,
           ROW_NUMBER() OVER(ORDER BY c.embedding <=> query_embedding) as rank
    FROM chunks c
    WHERE c.embedding IS NOT NULL
      AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
      AND (NOT exclude_toc OR COALESCE(c.is_toc, FALSE) = FALSE)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count * 3
  ),
  -- Combine and score results
  combined AS (
    SELECT
      c.id AS chunk_id,
      c.document_id,
      c.content,
      (1 - (c.embedding <=> query_embedding))::float AS similarity,
      c.metadata,
      d.title AS document_title,
      d.source AS document_source,
      d.metadata AS document_metadata,
      (COALESCE(1.0 / (rrf_k + f.rank), 0.0) + COALESCE(1.0 / (rrf_k + s.rank), 0.0))::float AS score
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    LEFT JOIN full_text f ON c.id = f.id
    LEFT JOIN semantic s ON c.id = s.id
    WHERE f.id IS NOT NULL OR s.id IS NOT NULL
  ),
  -- Limit chunks per document for diversity
  ranked AS (
    SELECT *,
           ROW_NUMBER() OVER(PARTITION BY combined.document_id ORDER BY combined.score DESC) as doc_rank
    FROM combined
  )
  SELECT
    ranked.chunk_id,
    ranked.document_id,
    ranked.content,
    ranked.similarity,
    ranked.metadata,
    ranked.document_title,
    ranked.document_source,
    ranked.document_metadata,
    ranked.score
  FROM ranked
  WHERE ranked.doc_rank <= max_per_doc
  ORDER BY ranked.score DESC
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION hybrid_search IS 'Hybrid search with RRF fusion. ef_search tunes HNSW recall/latency (default 100, use 200+ for high recall).';

COMMIT;
