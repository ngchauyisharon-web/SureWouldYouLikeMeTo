from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import settings


def build_outcome_scene_prompt(
    *,
    scenario_title: str,
    narrative_display: str,
    choice_label: str | None,
) -> str:
    core = (narrative_display or "").strip()[:520] or scenario_title
    parts = [f"Scenario: {scenario_title}.", f"Outcome: {core}"]
    if choice_label:
        parts.append(f"Action taken: {choice_label}.")
    return " ".join(parts)


def build_scenario_scene_prompt(
    *,
    scenario_title: str,
    tagline: str,
    body: str,
    turn0_static_line: str | None,
) -> str:
    """Story briefing for the session hero image (truncated for API limits)."""
    setup = (turn0_static_line or "").strip()
    blurb = f"{(tagline or '').strip()} {(body or '').strip()}".strip()
    parts = [f"Scenario: {scenario_title}."]
    if blurb:
        parts.append(f"Story: {blurb}")
    if setup:
        parts.append(f"Opening scene: {setup}")
    raw = " ".join(parts).strip()
    return raw[:560] if len(raw) > 560 else raw


def _full_dalle_prompt(scene_prompt: str) -> str:
    return (
        "South Park art style with Dumb Ways to Die style cartoon illustration. "
        "Flat vector art, bright bold colors, thick black outlines, simple friendly characters, "
        "funny and lighthearted. NO text or words anywhere in the image. "
        "Single isolated scene on plain background. "
        f"Scene: {scene_prompt}"
    )


def _azure_gateway_base() -> str:
    """Azure API Management root (e.g. https://hkust.azure-api.net), not …/deployments/…."""
    base = settings.azure_openai_endpoint.strip().rstrip("/")
    if base:
        return base
    img = settings.openai_images_endpoint.strip()
    if "/openai/deployments/" in img:
        return img.split("/openai/deployments/", 1)[0].rstrip("/")
    return ""


def generate_outcome_image_azure_sdk(api_key: str, scene_prompt: str) -> str | None:
    """Generate outcome image using DALL·E 3 via HKUST-style Azure OpenAI SDK."""
    log = logging.getLogger(__name__)
    endpoint = _azure_gateway_base()
    if not endpoint or not api_key.strip():
        return None
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key.strip(),
            api_version=(settings.openai_images_api_version.strip() or "2025-02-01-preview"),
        )
        model = settings.azure_image_deployment.strip() or "dall-e-3"
        response = client.images.generate(
            model=model,
            prompt=_full_dalle_prompt(scene_prompt),
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
        data = response.data or []
        if not data:
            return None
        b64 = data[0].b64_json
        return str(b64) if b64 else None
    except Exception as e:
        log.warning("azure_sdk_images_error: %s", e)
        return None


def is_image_generation_configured() -> bool:
    """True when scenario/outcome image jobs should run (HTTP deployments URL or Azure SDK gateway)."""
    if not settings.openai_api_key.strip():
        return False
    if settings.openai_images_use_azure_sdk and _azure_gateway_base():
        return True
    return bool(settings.openai_images_endpoint.strip())


async def generate_outcome_image_b64(scene_prompt: str) -> str | None:
    """HKUST / Azure OpenAI–style images/generations (DALL·E 3)."""
    log = logging.getLogger(__name__)
    api_key = settings.openai_api_key.strip()
    if settings.openai_images_use_azure_sdk:
        gateway = _azure_gateway_base()
        if gateway and api_key:
            b64_sdk = await asyncio.to_thread(generate_outcome_image_azure_sdk, api_key, scene_prompt)
            if b64_sdk:
                return b64_sdk
            log.info("image_gen_azure_sdk_failed_trying_http")

    endpoint = settings.openai_images_endpoint.strip()
    if not endpoint or not api_key:
        return None

    url = f"{endpoint.rstrip('/')}/images/generations"
    if settings.openai_images_api_version:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api-version={settings.openai_images_api_version}"

    auth = (settings.openai_auth_style or "bearer").lower()
    if auth == "azure":
        headers = {"api-key": settings.openai_api_key, "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "prompt": _full_dalle_prompt(scene_prompt),
            "size": "1024x1024",
            "n": 1,
            "response_format": "b64_json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "dall-e-3",
            "prompt": _full_dalle_prompt(scene_prompt),
            "size": "1024x1024",
            "n": 1,
            "response_format": "b64_json",
        }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
        except httpx.RequestError as e:
            logging.getLogger(__name__).warning("images_generations_network_error: %s", e)
            return None
        if resp.status_code >= 400:
            logging.getLogger(__name__).warning(
                "images_generations_http_%s: %s",
                resp.status_code,
                (resp.text or "")[:500],
            )
            return None
        data = resp.json()

    data_list = data.get("data") or []
    if not data_list:
        return None
    b64 = data_list[0].get("b64_json")
    return str(b64) if b64 else None
