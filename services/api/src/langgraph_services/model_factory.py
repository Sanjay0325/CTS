"""Model factory - convert CTS profile to LangChain chat model for unified handling."""

import hashlib
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.constants import GEMINI_MODEL_ALIASES

logger = logging.getLogger(__name__)


def _prompt_cache_key(prefix: str) -> str:
    """Stable key for OpenAI prompt caching. Same prefix = cache hit."""
    return f"cts_{hashlib.sha256(prefix.encode()).hexdigest()[:24]}"


def create_chat_model_from_profile(
    profile: dict,
    temperature: float = 0.7,
    streaming: bool = True,
    request_timeout: float = 300.0,
    cache_key_prefix: str | None = None,
) -> BaseChatModel:
    """
    Create a LangChain chat model from CTS model profile.
    Handles OpenAI-compatible, Gemini, Ollama, Groq, OpenRouter, etc.
    Includes retry logic for transient failures.
    """
    api_style = (profile.get("api_style") or "openai").lower()
    base_url = (profile.get("provider_base_url") or "").rstrip("/")
    model = profile.get("model_name") or "gpt-4"
    api_key = (profile.get("api_key") or "").strip() or "not-needed"  # Ollama ignores it

    logger.info("Creating chat model: style=%s model=%s base=%s", api_style, model, base_url[:50])

    if api_style == "gemini":
        model = GEMINI_MODEL_ALIASES.get(model, model)
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            streaming=streaming,
            convert_system_message_to_human=True,
            max_retries=2,
        )

    kwargs: dict = {
        "model": model,
        "api_key": api_key,
        "base_url": f"{base_url}/v1",
        "temperature": temperature,
        "streaming": streaming,
        "request_timeout": request_timeout,
        "max_retries": 2,
    }
    if cache_key_prefix and "openai.com" in base_url.lower():
        try:
            kwargs["model_kwargs"] = {"prompt_cache_key": _prompt_cache_key(cache_key_prefix)}
        except Exception:
            pass
    return ChatOpenAI(**kwargs)

