-- Up migration for OpenAI `text-embedding-3-small` (1536 dimensions)

-- 1. Drop existing index
DROP INDEX IF EXISTS asset_embeddings_embedding_idx;

-- 2. Alter the embedding column (this will lose data, but it's okay for an E2E test/reset)
ALTER TABLE asset_embeddings
  ALTER COLUMN embedding TYPE vector(1536);

-- 3. Re-create the index
CREATE INDEX asset_embeddings_embedding_idx ON asset_embeddings USING hnsw (embedding vector_cosine_ops);

-- 4. Re-create the matching function to accept 1536 dimensions
DROP FUNCTION IF EXISTS find_similar_assets(vector(768), float, int);

CREATE OR REPLACE FUNCTION find_similar_assets(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  asset_id uuid,
  client_id uuid,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    ae.asset_id,
    ae.client_id,
    1 - (ae.embedding <=> query_embedding) AS similarity
  FROM asset_embeddings ae
  WHERE 1 - (ae.embedding <=> query_embedding) > match_threshold
  ORDER BY ae.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
