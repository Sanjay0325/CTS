-- Chat history, RAG documents, and response metadata
-- Run in Supabase SQL Editor

-- Add updated_at to conversations for ordering
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
UPDATE public.conversations SET updated_at = created_at WHERE updated_at IS NULL;
ALTER TABLE public.conversations ALTER COLUMN updated_at SET DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON public.conversations(user_id, updated_at DESC);

-- document_collections: user's named "external DBs" for RAG search
CREATE TABLE IF NOT EXISTS public.document_collections (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- documents: uploaded privacy/other documents
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES public.document_collections(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- document_chunks: for RAG with embeddings (1536 = OpenAI text-embedding-3-small)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding extensions.vector(1536),  -- NULL until embedded
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- message_metadata: tools used, external DBs used per assistant message
CREATE TABLE IF NOT EXISTS public.message_metadata (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    tools_used JSONB DEFAULT '[]',
    external_dbs_used JSONB DEFAULT '[]',
    in_context_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(message_id)
);

-- collection_documents: link documents to collections (many-to-many)
CREATE TABLE IF NOT EXISTS public.collection_documents (
    collection_id UUID NOT NULL REFERENCES public.document_collections(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (collection_id, document_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_document_collections_user ON public.document_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_collection ON public.documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user ON public.document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_message_metadata_conversation ON public.message_metadata(conversation_id);

-- Vector index for RAG (run after chunks exist; ivfflat needs rows)
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- RLS
ALTER TABLE public.document_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collection_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own document_collections" ON public.document_collections
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own documents" ON public.documents
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own document_chunks" ON public.document_chunks
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own message_metadata" ON public.message_metadata
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.messages m WHERE m.id = message_id AND m.user_id = auth.uid())
    );

CREATE POLICY "Users manage collection_documents" ON public.collection_documents
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.document_collections c WHERE c.id = collection_id AND c.user_id = auth.uid())
    );

-- Update conversation.updated_at when messages are added
CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.conversations SET updated_at = NOW() WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_messages_updated ON public.messages;
CREATE TRIGGER trg_messages_updated
    AFTER INSERT ON public.messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_updated_at();
