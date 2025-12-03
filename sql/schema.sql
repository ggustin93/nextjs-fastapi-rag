CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP INDEX IF EXISTS idx_chunks_embedding;
DROP INDEX IF EXISTS idx_chunks_document_id;
DROP INDEX IF EXISTS idx_documents_metadata;

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX idx_documents_created_at ON documents (created_at DESC);

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    is_toc BOOLEAN DEFAULT FALSE,  -- True if chunk is Table of Contents content
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1);
CREATE INDEX idx_chunks_document_id ON chunks (document_id);
CREATE INDEX idx_chunks_chunk_index ON chunks (document_id, chunk_index);
-- GIN index for French Full-Text Search performance
CREATE INDEX idx_chunks_content_fts ON chunks USING GIN (to_tsvector('french', content));

-- Fixed match_chunks with similarity_threshold support
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT,
    document_metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        c.metadata,
        d.title AS document_title,
        d.source AS document_source,
        d.metadata AS document_metadata
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
      AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Hybrid search combining vector similarity and French keyword matching
-- Uses Reciprocal Rank Fusion (RRF) to combine results
-- Optionally excludes TOC chunks marked during ingestion
-- Limits chunks per document for source diversity (max_per_doc parameter)
CREATE OR REPLACE FUNCTION hybrid_search(
  query_text text,
  query_embedding vector(1536),
  match_count int DEFAULT 20,
  similarity_threshold float DEFAULT 0.0,
  rrf_k int DEFAULT 60,
  exclude_toc boolean DEFAULT TRUE,
  max_per_doc int DEFAULT 3
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

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
