"""Shared constants used across services."""

# Ollama models that support tool/function calling. Base llama3/llama2 do NOT.
# See https://docs.ollama.com/capabilities/tool-calling
OLLAMA_TOOL_CAPABLE_PATTERNS = (
    "llama3.1", "llama3.2", "llama4",  # Llama 3.1+ only
    "qwen", "qwen2", "qwen3",          # Qwen family
    "mistral-nemo", "mistral-small",   # Mistral
    "command-r", "command-r+",
    "firefunction", "devstral",
)

# Deprecated Gemini model names -> current equivalents for model_factory and chat_service
GEMINI_MODEL_ALIASES = {
    "gemini-1.5-flash": "gemini-2.0-flash",
    "gemini-1.5-pro": "gemini-2.0-flash",
    "gemini-1.5-flash-8b": "gemini-2.0-flash",
    "gemini-1.5-flash-latest": "gemini-2.0-flash",
}
