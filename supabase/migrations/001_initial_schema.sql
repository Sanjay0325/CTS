-- Enable required extensions explicitly in the extensions schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA extensions;

-- Enable Vault for secure secret storage
CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA extensions CASCADE;

-- model_profiles: stores user-defined model entries
CREATE TABLE public.model_profiles (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    provider_base_url TEXT NOT NULL,
    api_style TEXT NOT NULL DEFAULT 'openai',  -- 'openai' | 'anthropic' | 'custom'
    model_name TEXT NOT NULL,
    model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- model_profile_secrets: maps profiles to encrypted API keys in Vault
CREATE TABLE public.model_profile_secrets (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES public.model_profiles(id) ON DELETE CASCADE,
    vault_secret_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(profile_id)
);

-- conversations: stores conversation metadata
CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- messages: stores individual chat messages
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- memory_items: stores persistent memory (external memory)
CREATE TABLE public.memory_items (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('summary', 'fact', 'preference')),
    text TEXT NOT NULL,
    source TEXT,  -- e.g., conversation_id or 'manual'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding extensions.vector(1536)  -- Explicitly point to the extensions schema for vector
);

-- mcp_servers: stores registered MCP server configurations
CREATE TABLE public.mcp_servers (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    server_url TEXT NOT NULL,
    transport TEXT NOT NULL DEFAULT 'streamable-http',  -- 'streamable-http' | 'stdio'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- user_settings: stores active model profile and other UI preferences
CREATE TABLE public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    active_profile_id UUID REFERENCES public.model_profiles(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_model_profiles_user_id ON public.model_profiles(user_id);
CREATE INDEX idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON public.messages(conversation_id);
CREATE INDEX idx_messages_created_at ON public.messages(conversation_id, created_at);
CREATE INDEX idx_memory_items_user_id ON public.memory_items(user_id);
CREATE INDEX idx_memory_items_kind ON public.memory_items(user_id, kind);
CREATE INDEX idx_memory_items_created_at ON public.memory_items(user_id, created_at DESC);
CREATE INDEX idx_mcp_servers_user_id ON public.mcp_servers(user_id);

-- Row Level Security (RLS)
ALTER TABLE public.model_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_profile_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mcp_servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own data
CREATE POLICY "Users can manage own model_profiles"
    ON public.model_profiles FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can manage own model_profile_secrets"
    ON public.model_profile_secrets FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.model_profiles p WHERE p.id = profile_id AND p.user_id = auth.uid())
    )
    WITH CHECK (
        EXISTS (SELECT 1 FROM public.model_profiles p WHERE p.id = profile_id AND p.user_id = auth.uid())
    );

CREATE POLICY "Users can manage own conversations"
    ON public.conversations FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can manage own messages"
    ON public.messages FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can manage own memory_items"
    ON public.memory_items FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can manage own mcp_servers"
    ON public.mcp_servers FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can manage own user_settings"
    ON public.user_settings FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);