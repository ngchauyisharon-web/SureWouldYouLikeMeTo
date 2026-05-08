from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import settings


async def stream_chat_completion(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """Yield content deltas from an OpenAI-compatible chat completions stream."""
    if not settings.openai_api_key:
        async for chunk in _mock_stream(messages):
            yield chunk
        return

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = parsed.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta


async def _mock_stream(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """Deterministic offline narrator when no API key is set."""
    last = messages[-1]["content"] if messages else ""
    snippet = (
        "The slide deck gently combusts. Someone schedules a post-mortem titled "
        "'Learning Opportunity.' You nod like this was always the plan."
    )
    if "chose" in last:
        choice = last.split("The player chose:", 1)[-1].strip().split("\n")[0]
        text = (
            f"You picked: {choice}. "
            "The room pretends alignment improved. Metrics shimmer with unjustified optimism."
        )
    else:
        text = snippet
    for i in range(0, len(text), 6):
        yield text[i : i + 6]
        await __import__("asyncio").sleep(0.03)
