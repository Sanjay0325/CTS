-- Safe migration: add vector index and remind_at timestamp column
-- SAFE: All operations are additive only (IF NOT EXISTS), no data loss or modification

-- 1. Vector index for RAG performance (was commented out in migration 003).
-- Uses HNSW for better performance on Supabase (no row-count requirement like ivfflat).
-- This dramatically speeds up vector similarity search in document_chunks.
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
ON public.document_chunks
USING hnsw (embedding extensions.vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 2. Add a proper TIMESTAMPTZ column alongside the TEXT remind_at.
-- We keep the existing remind_at TEXT column untouched to avoid breaking anything.
-- New code can use remind_at_ts for efficient time-based queries.
ALTER TABLE public.user_reminders
ADD COLUMN IF NOT EXISTS remind_at_ts TIMESTAMPTZ DEFAULT NULL;

-- Try to populate remind_at_ts from existing remind_at values (best effort, ISO format only).
-- This is a safe UPDATE that only touches rows where remind_at_ts is NULL.
UPDATE public.user_reminders
SET remind_at_ts = remind_at::TIMESTAMPTZ
WHERE remind_at_ts IS NULL
  AND remind_at IS NOT NULL
  AND remind_at != ''
  AND remind_at ~ '^\d{4}-\d{2}-\d{2}';

-- Index for efficient "reminders due soon" queries
CREATE INDEX IF NOT EXISTS idx_user_reminders_ts
ON public.user_reminders(user_id, remind_at_ts)
WHERE remind_at_ts IS NOT NULL;
