-- Prompt trace for each message - visualize what was used (RAG, memory, tools, model)
ALTER TABLE public.message_metadata ADD COLUMN IF NOT EXISTS prompt_trace JSONB DEFAULT NULL;
ALTER TABLE public.message_metadata ADD COLUMN IF NOT EXISTS model_used TEXT DEFAULT NULL;

COMMENT ON COLUMN public.message_metadata.prompt_trace IS 'Trace of prompt assembly: system_prompt_preview, rag_chunks, memory_items, tools_available, model_used';
