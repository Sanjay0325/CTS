-- Memory Items Vector Search
-- Adds vector similarity search RPC for agent's external memory
-- Creates HNSW index on the memory_items table for efficient search

-- Create HNSW index for cosine similarity over memory embeddings
CREATE INDEX IF NOT EXISTS idx_memory_items_embedding ON public.memory_items
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Function: semantic search over memory items
CREATE OR REPLACE FUNCTION public.match_memory_items(
  query_embedding extensions.vector(1536),
  filter_user_id uuid,
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.5
)
RETURNS TABLE (
  id uuid,
  kind text,
  text text,
  source text,
  created_at timestamptz,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.kind,
    m.text,
    m.source,
    m.created_at,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM public.memory_items m
   WHERE
    m.embedding IS NOT NULL
    AND m.user_id = filter_user_id
    AND (1 - (m.embedding <=> query_embedding)) > match_threshold
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
