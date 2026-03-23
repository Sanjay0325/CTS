"""Document and RAG service - upload, chunk, embed, search."""

import re
from uuid import UUID, uuid4

import httpx


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if end < len(text) else len(text)
    return chunks


def get_embeddings_sync(texts: list[str], api_key: str) -> list[list[float]]:
    """Get embeddings from OpenAI API (sync). Returns list of 1536-dim vectors."""
    if not texts or not api_key:
        return []
    with httpx.Client(timeout=60) as client:
        r = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": texts},
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return [d["embedding"] for d in data.get("data", [])]


async def get_embeddings(texts: list[str], api_key: str) -> list[list[float]]:
    """Get embeddings from OpenAI API (async). Returns list of 1536-dim vectors."""
    if not texts or not api_key:
        return []
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": texts},
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return [d["embedding"] for d in data.get("data", [])]


def simple_search_chunks(content: str, query: str) -> list[tuple[str, float]]:
    """Simple text search (no embeddings) - keyword overlap score."""
    q = set(re.findall(r"\w+", query.lower()))
    if not q:
        return [(content, 0.0)]
    c = set(re.findall(r"\w+", content.lower()))
    overlap_count = len(q & c)
    score = overlap_count / len(q) if q else 0
    return [(content, score)]
