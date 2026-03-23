-- Fallback for API keys when Vault is unavailable (e.g. extension not enabled)
ALTER TABLE public.model_profile_secrets ALTER COLUMN vault_secret_id DROP NOT NULL;
ALTER TABLE public.model_profile_secrets ADD COLUMN IF NOT EXISTS api_key_plain TEXT;
