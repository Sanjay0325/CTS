"""Test Ollama output for save_note tool prompt - no auth needed."""
import asyncio
import json
import httpx

SYSTEM = """You are a helpful AI. You have this tool: save_note(title, content).
When the user asks to save a note, output ONLY this JSON (no other text):
{"tool": "save_note", "args": {"title": "TITLE", "content": "CONTENT"}}
Example: user says "my name is Akash, save note with title as my name" → output {"tool": "save_note", "args": {"title": "Akash", "content": "proud prompt of myself"}}."""

USER = "hloo my bhai, hello, my name is akash and i am CP programming god with guardian badge. i want a note with title as my name and description about proud prompt of myself, do it with given mcp tool"

async def main():
    url = "http://localhost:11434/v1/chat/completions"
    payload = {
        "model": "llama3:latest",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, json=payload)
        print("Status:", r.status_code)
        if r.status_code != 200:
            print(r.text)
            return
        data = r.json()
        content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        print("Raw response:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        # Try to parse as tool call
        if "{" in content and '"tool"' in content:
            start = content.find("{")
            depth = 0
            for i, ch in enumerate(content[start:], start):
                if ch == "{": depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            j = json.loads(content[start:i+1])
                            if j.get("tool"):
                                print("Parsed tool call:", j)
                                return
                        except json.JSONDecodeError:
                            pass
        print("No valid tool JSON found in response")

if __name__ == "__main__":
    asyncio.run(main())
