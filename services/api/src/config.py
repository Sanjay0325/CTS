"""
Application configuration from environment.

Loads .env from project root. Keys: SUPABASE_*, DATABASE_URL, OPENAI_API_KEY,
EMBEDDING_API_KEY, OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL, etc.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Database
    database_url: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # MCP
    mcp_allowed_origins: str = "localhost,127.0.0.1"

    # RAG embeddings (OpenAI text-embedding-3-small)
    openai_api_key: str = ""
    embedding_api_key: str = ""  # Falls back to openai_api_key if set

    # Ollama (local Llama) - available to all users as "default" model
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3:latest"  # Override via OLLAMA_DEFAULT_MODEL

    # LangSmith (optional) - trace visualization at smith.langchain.com
    langsmith_tracing: str = "false"  # LANGSMITH_TRACING=true to enable
    langsmith_api_key: str = ""       # LANGSMITH_API_KEY
    langsmith_project: str = "cts"    # LANGSMITH_PROJECT


settings = Settings()


def get_embedding_api_key() -> str:
    """API key for embeddings. Prefer embedding_api_key, fallback to openai_api_key."""
    return settings.embedding_api_key or settings.openai_api_key or ""
