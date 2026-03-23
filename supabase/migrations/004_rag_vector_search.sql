-- RAG: Vector search function for document_chunks
-- Requires document_chunks.embedding to be populated (1536-dim OpenAI embeddings)
-- Run after 003_chat_history_rag_metadata.sql

-- Enable vector search: create index when we have rows (uncomment after data exists)
-- CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON public.document_chunks
--   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function: semantic search over document chunks
CREATE OR REPLACE FUNCTION public.match_document_chunks(
  query_embedding extensions.vector(1536),
  filter_collection_ids uuid[] DEFAULT NULL,
  filter_user_id uuid DEFAULT NULL,
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.5
)
RETURNS TABLE (
  id uuid,
  content text,
  document_id uuid,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.content,
    dc.document_id,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM public.document_chunks dc
  JOIN public.documents d ON d.id = dc.document_id
  WHERE
    dc.embedding IS NOT NULL
    AND (filter_user_id IS NULL OR dc.user_id = filter_user_id)
    AND (filter_collection_ids IS NULL OR d.collection_id = ANY(filter_collection_ids))
    AND (1 - (dc.embedding <=> query_embedding)) > match_threshold
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
