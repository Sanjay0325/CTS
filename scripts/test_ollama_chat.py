#!/usr/bin/env python3
"""Test Ollama/llama3:latest chat via CTS API. Run with API server on port 8000."""

import asyncio
import json
import os
import sys

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Use a test JWT or skip auth if your API allows
# For full test: set AUTH_TOKEN env or use Supabase session
AUTH = os.getenv("AUTH_TOKEN", "")


async def test_ollama_models():
    """Test GET /ollama/models (requires auth in real API)."""
    url = f"{API_URL}/ollama/models"
    headers = {"Authorization": f"Bearer {AUTH}"} if AUTH else {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(url, headers=headers)
            print(f"GET /ollama/models -> {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  available: {data.get('available')}")
                print(f"  models: {[m.get('name') for m in data.get('models', [])]}")
                print(f"  default: {data.get('default_model')}")
            else:
                print(f"  {r.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


async def test_ollama_chat_stream():
    """Test POST /chat/stream with ollama_model=llama3:latest."""
    url = f"{API_URL}/chat/stream"
    headers = {"Content-Type": "application/json"}
    if AUTH:
        headers["Authorization"] = f"Bearer {AUTH}"
    body = {
        "message": "Say hello in 5 words.",
        "ollama_model": "llama3:latest",
        "profile_id": None,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=body) as r:
                print(f"POST /chat/stream (ollama) -> {r.status_code}")
                if r.status_code != 200:
                    text = await r.aread()
                    print(f"  {text.decode()[:300]}")
                    return
                full = []
                async for line in r.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            continue
                        try:
                            ev = json.loads(data)
                            t = ev.get("type")
                            if t == "text":
                                full.append(ev.get("content", ""))
                            elif t == "error":
                                print(f"  ERROR: {ev.get('content')}")
                            elif t == "done":
                                print(f"  conversation_id: {ev.get('conversation_id')}")
                        except json.JSONDecodeError:
                            pass
                print(f"  Response: {''.join(full)[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


async def main():
    print("=== Ollama / llama3:latest Test ===\n")
    await test_ollama_models()
    print()
    await test_ollama_chat_stream()
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
