"""MCP Translator - translate text between languages."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Translator", json_response=True, host="0.0.0.0", port=8007, stateless_http=True)

# Mock translations - replace with real API (e.g. Google Translate, DeepL)
_TRANSLATIONS = {
    ("hello", "es"): "hola",
    ("hello", "fr"): "bonjour",
    ("hello", "de"): "hallo",
    ("hello", "ja"): "こんにちは",
    ("thank you", "es"): "gracias",
}


@mcp.tool()
def translate(text: str, target_lang: str = "es", source_lang: str = "en") -> str:
    """Translate text to target language. Use ISO 639-1 codes (en, es, fr, de, ja, etc.)."""
    key = (text.lower().strip(), target_lang.lower())
    if key in _TRANSLATIONS:
        return _TRANSLATIONS[key]
    return f"[Demo] Translated '{text}' to {target_lang}: (use real API for production)"


@mcp.tool()
def list_languages() -> str:
    """List supported language codes."""
    return "en (English), es (Spanish), fr (French), de (German), ja (Japanese), zh (Chinese), hi (Hindi)"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
