-- pgvector HNSW index for SigLIP So400m embeddings (1152-dim)
-- Run after migrating embedding_dimension from 768 → 1152 and re-vectorizing assets.

CREATE INDEX IF NOT EXISTS idx_asset_embeddings_hnsw
  ON asset_embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
