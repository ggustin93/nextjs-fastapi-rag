-- Migration: Upgrade pgvector from IVFFlat to HNSW index
-- HNSW provides ~10x faster search with better recall
-- Run this migration against your Supabase database
--
-- Parameters:
--   m = 24: Maximum connections per layer (higher = better recall, more memory)
--   ef_construction = 100: Build-time search depth (higher = better quality, slower build)
--
-- Query-time tuning:
--   ef_search (default 100): Search depth at query time (higher = better recall, slower)
--   Set via: SET hnsw.ef_search = 200;

BEGIN;

-- Drop old IVFFlat index
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Create HNSW index for vector similarity search
-- Uses cosine distance operator (vector_cosine_ops) matching hybrid_search function
CREATE INDEX idx_chunks_embedding_hnsw ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Add comment documenting the index parameters
COMMENT ON INDEX idx_chunks_embedding_hnsw IS 'HNSW index for vector similarity search. m=24, ef_construction=100. Tune ef_search at query time (default 100).';

-- Function to dynamically set ef_search for query-time tuning
-- Higher values improve recall at cost of latency
-- Recommended: 100 for balanced, 200+ for high-recall scenarios
CREATE OR REPLACE FUNCTION set_hnsw_ef_search(ef_value INTEGER DEFAULT 100)
RETURNS VOID AS $$
BEGIN
    IF ef_value < 10 OR ef_value > 1000 THEN
        RAISE EXCEPTION 'ef_search must be between 10 and 1000, got %', ef_value;
    END IF;
    EXECUTE format('SET LOCAL hnsw.ef_search = %s', ef_value);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_hnsw_ef_search IS 'Set HNSW ef_search parameter for current transaction. Higher values = better recall, slower queries.';

COMMIT;

-- Verification query (run after migration):
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'chunks' AND indexname LIKE '%embedding%';
