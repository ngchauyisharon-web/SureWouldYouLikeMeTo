from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import settings


def _chat_target_is_azure_deployment() -> bool:
    """True when chat URL is an Azure OpenAI / APIM deployment path (api-key, no model in body)."""
    return "/openai/deployments/" in settings.openai_base_url.strip().lower()


async def chat_completion_text(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 280,
    temperature: float = 1.0,
) -> str:
    """Single-voice chat completion (non-streaming). Used by NeuroBot coach."""
    if not settings.openai_api_key:
        return _mock_coach_reply(messages)

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    if settings.openai_api_version:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api-version={settings.openai_api_version}"

    if _chat_target_is_azure_deployment():
        headers = {
            "api-key": settings.openai_api_key,
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    else:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.openai_model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        log = logging.getLogger(__name__)
        detail = ""
        try:
            detail = (e.response.text or "")[:400].replace("\n", " ")
        except Exception:
            pass
        log.warning("chat_completion_text HTTP %s: %s body_prefix=%s", e.response.status_code, e, detail)
        return _mock_coach_reply(messages)
    except httpx.RequestError as e:
        logging.getLogger(__name__).warning("chat_completion_text: %s", e)
        return _mock_coach_reply(messages)

    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    return (content or "").strip()


def _mock_coach_reply(messages: list[dict[str, str]]) -> str:
    last = (messages[-1].get("content", "") if messages else "").lower()
    fishing = (
        "correct answer" in last
        or "right answer" in last
        or "what should i choose" in last
        or "which option" in last
        or "tell me the answer" in last
        or "which one is right" in last
        or "which path" in last
    )
    if fishing:
        return (
            "Nice try. That kind of question costs you offline integrity points. "
            "I'm here to make you think, not to think for you. Ask about the situation instead."
        )
    return (
        "Look at who eats the risk if this blows up — that's usually where the right move hides. "
        "What would you actually do in the room?"
    )


async def stream_chat_completion(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    """Yield content deltas from an OpenAI-compatible chat completions stream."""
    if not settings.openai_api_key:
        async for chunk in _mock_stream(messages):
            yield chunk
        return

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    if settings.openai_api_version:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api-version={settings.openai_api_version}"

    if _chat_target_is_azure_deployment():
        headers = {
            "api-key": settings.openai_api_key,
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {"messages": messages, "stream": True}
    else:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
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
    if "typed into NeuroBot" in last:
        text = (
            "NeuroBot logs your answer beside three contradictory KPIs. "
            "Morale holds steady at 'technically printable.'\n"
            "SCORE_CHANGE: -2"
        )
    elif "chose" in last:
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
