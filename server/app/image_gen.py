from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

import httpx

from app.azure_openai_client import get_azure_openai_client
from app.config import settings


@dataclass(frozen=True)
class ImageGenResult:
    b64: str | None
    """Short explanation on failure (safe to return to API clients — no secrets)."""
    detail: str | None = None


def _safe_detail(msg: str | None, max_len: int = 280) -> str | None:
    if not msg or not str(msg).strip():
        return None
    s = str(msg).strip().replace("\n", " ")
    return s[:max_len] if len(s) > max_len else s


def _error_from_http_body(status_code: int, text: str) -> str | None:
    trimmed = (text or "").strip()
    if not trimmed:
        return _safe_detail(f"HTTP {status_code}")
    try:
        data = json.loads(trimmed)
        return _error_from_api_json(data) or _safe_detail(f"HTTP {status_code}: {trimmed[:200]}")
    except json.JSONDecodeError:
        return _safe_detail(f"HTTP {status_code}: {trimmed[:220]}")


def _error_from_api_json(data: dict[str, Any]) -> str | None:
    err = data.get("error")
    if err is None:
        return None
    if isinstance(err, str):
        return _safe_detail(err)
    if isinstance(err, dict):
        code = err.get("code")
        msg = err.get("message")
        parts = [p for p in (code, msg) if p]
        if parts:
            return _safe_detail(": ".join(str(p) for p in parts))
        return _safe_detail(str(err))
    return _safe_detail(str(err))


def _sync_fetch_image_url_as_b64(image_url: str) -> str | None:
    log = logging.getLogger(__name__)
    try:
        req = Request(image_url, headers={"User-Agent": "SureWouldYouLikeMeTo/0.1"})
        with urlopen(req, timeout=90) as r:
            raw = r.read()
        return base64.standard_b64encode(raw).decode("ascii")
    except Exception as e:
        log.warning("image_url_fetch_sync_error: %s", e)
        return None


async def _async_fetch_image_url_as_b64(client: httpx.AsyncClient, image_url: str) -> str | None:
    log = logging.getLogger(__name__)
    try:
        r = await client.get(image_url, timeout=90.0)
        if r.status_code >= 400:
            log.warning(
                "image_url_fetch_http_%s: %s",
                r.status_code,
                (r.text or "")[:200],
            )
            return None
        return base64.standard_b64encode(r.content).decode("ascii")
    except httpx.RequestError as e:
        log.warning("image_url_fetch_error: %s", e)
        return None


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


def build_ending_scene_prompt(
    *,
    scenario_title: str,
    epilogue_narrative: str,
    choice_label: str | None,
    neural_score: int,
) -> str:
    """Final-run illustration: epilogue + last beat (truncated for API limits)."""
    core = (epilogue_narrative or "").strip()[:480] or scenario_title
    parts = [
        "Epilogue / final scene after the player finished the scenario.",
        f"Scenario: {scenario_title}.",
        f"How the story concluded: {core}",
    ]
    if choice_label:
        parts.append(f"Last choice taken: {choice_label}.")
    parts.append(f"Final neural score (0–100, higher is more ethical/cautious): {neural_score}.")
    raw = " ".join(parts).strip()
    return raw[:560] if len(raw) > 560 else raw


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


def build_question_turn_prompt(
    *,
    scenario_title: str,
    tagline: str,
    body: str,
    static_line: str | None,
    turn_index: int,
    total_turns: int,
) -> str:
    """Scene for the dilemma posed this turn (hero polaroid next to the question)."""
    setup = (static_line or "").strip()
    blurb = f"{(tagline or '').strip()} {(body or '').strip()}".strip()
    parts = [f"Scenario: {scenario_title}.", f"Turn {turn_index + 1} of {total_turns}."]
    if blurb:
        parts.append(f"Context: {blurb}")
    if setup:
        parts.append(f"The dilemma this moment: {setup}")
    raw = " ".join(parts).strip()
    return raw[:560] if len(raw) > 560 else raw


def build_post_choice_scene_prompt(
    *,
    scenario_title: str,
    completed_turn_index: int,
    total_turns: int,
    choice_label: str | None,
    free_text_excerpt: str | None,
    narrative_display: str,
    free_text_max: int = 120,
    narrative_max: int = 520,
) -> str:
    """Scene after a choice/free-text + narrator outcome (hero polaroid for the next beat)."""
    parts = [
        f"Scenario: {scenario_title}.",
        f"After turn {completed_turn_index + 1} of {total_turns}.",
    ]
    if choice_label and str(choice_label).strip():
        parts.append(f"Player chose: {str(choice_label).strip()}")
    elif free_text_excerpt and str(free_text_excerpt).strip():
        ex = str(free_text_excerpt).strip().replace("\n", " ")
        if len(ex) > free_text_max:
            ex = ex[: free_text_max - 1].rstrip() + "…"
        parts.append(f"Player said: {ex}")
    out = (narrative_display or "").strip().replace("\n", " ")
    if len(out) > narrative_max:
        out = out[: narrative_max - 1].rstrip() + "…"
    if out:
        parts.append(f"What happened next: {out}")
    raw = " ".join(parts).strip()
    return raw[:600] if len(raw) > 600 else raw


# MiniMax `prompt` max length (see platform docs).
MINIMAX_PROMPT_MAX = 1500

# Shared visual recipe: explicit South Park series look (Trey Parker / Matt Stone cutout animation).
_IMAGE_STYLE_CORE = (
    "Render in the same visual style as the South Park TV series: 2D construction-paper and cardstock cutout "
    "characters and props with bold black outer outlines, flat simple fills, almost no gradients or surface "
    "texture, and no 3D depth cues. "
    "Character design language: large round white eyes with tiny black dot pupils when eyes are visible; "
    "small simple oval or line mouths; blocky geometric hair, hats, and clothing; squat proportions and "
    "stiff puppet-like poses as if paper on a simple rig. "
    "Adult animated satire comedy tone—playful and exaggerated, not photorealistic gore. "
    "NOT photorealistic, NOT anime, NOT Pixar-style 3D, NOT painterly illustration. "
    "NO text, letters, logos, captions, UI, or watermarks anywhere. "
    "One clear readable tableau on a simple flat-color or plain paper-colored backdrop. "
)


def _image_style_prefix() -> str:
    extra = settings.image_style_label.strip()
    if extra:
        return f"{_IMAGE_STYLE_CORE}{extra}. "
    return _IMAGE_STYLE_CORE


def _full_image_prompt(scene_prompt: str, *, max_total: int | None = None) -> str:
    """Full prompt = fixed style prefix + scene description. Optionally cap length (MiniMax: 1500)."""
    scene = (scene_prompt or "").strip().replace("\n", " ")
    prefix = _image_style_prefix()
    header = f"{prefix}Scene: "
    body = f"{header}{scene}"
    cap = max_total
    if cap is None or len(body) <= cap:
        return body
    room = cap - len(header)
    if room < 24:
        return body[:cap]
    trimmed = scene[:room]
    if len(scene) > room:
        trimmed = trimmed[: room - 1].rstrip() + "…"
    return header + trimmed


def _resolved_images_endpoint() -> str:
    """Deployments URL for REST image calls; mirrors config aliases when explicit URL unset."""
    ep = settings.openai_images_endpoint.strip()
    if ep:
        return ep
    az = settings.azure_openai_endpoint.strip().rstrip("/")
    img = settings.azure_image_deployment.strip()
    if az and img:
        return f"{az}/openai/deployments/{img}"
    return ""


def _azure_gateway_base() -> str:
    """Azure API Management root (e.g. https://hkust.azure-api.net), not …/deployments/…."""
    base = settings.azure_openai_endpoint.strip().rstrip("/")
    if base:
        return base
    dep_url = _resolved_images_endpoint()
    if "/openai/deployments/" in dep_url:
        return dep_url.split("/openai/deployments/", 1)[0].rstrip("/")
    img = settings.openai_images_endpoint.strip()
    if "/openai/deployments/" in img:
        return img.split("/openai/deployments/", 1)[0].rstrip("/")
    return ""


def _azure_style_headers(api_key: str) -> dict[str, str]:
    """Many Azure APIM gateways accept api-key; some require Ocp-Apim-Subscription-Key (often same value)."""
    key = api_key.strip()
    return {
        "api-key": key,
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }


def generate_outcome_image_sdk_sync(scene_prompt: str) -> ImageGenResult:
    """Generate outcome image using DALL·E 3 via Azure OpenAI SDK (gateway root + deployment name)."""
    log = logging.getLogger(__name__)
    api_key = settings.openai_api_key.strip()
    endpoint = _azure_gateway_base()
    if not endpoint or not api_key:
        return ImageGenResult(None, "Missing Azure gateway endpoint or API key.")

    try:
        # Same gateway as Colab; images may use OPENAI_IMAGES_API_VERSION for the SDK call.
        client = get_azure_openai_client(
            api_version=settings.openai_images_api_version.strip() or None,
        )
        model = settings.azure_image_deployment.strip() or "dall-e-3"
        response = client.images.generate(
            model=model,
            prompt=_full_image_prompt(scene_prompt),
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
        data = response.data or []
        if not data:
            return ImageGenResult(None, "Azure SDK returned no image entries.")
        item = data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            return ImageGenResult(str(b64), None)
        url = getattr(item, "url", None)
        if url:
            b64_fb = _sync_fetch_image_url_as_b64(str(url))
            if b64_fb:
                log.info("image_gen_sdk_using_url_fallback")
                return ImageGenResult(b64_fb, None)
            return ImageGenResult(None, "Image URL returned but download failed.")
        return ImageGenResult(None, "Azure SDK payload had neither b64_json nor url.")
    except Exception as e:
        log.warning("azure_sdk_images_error: %s", e)
        return ImageGenResult(None, _safe_detail(str(e)) or "Azure SDK image call failed.")


def is_image_generation_configured() -> bool:
    """True when polaroid jobs can run for the configured image provider."""
    if settings.image_provider == "minimax":
        return bool(settings.minimax_api_key.strip())
    if not settings.openai_api_key.strip():
        return False
    if settings.openai_images_endpoint.strip():
        return True
    return bool(_azure_gateway_base().strip() and settings.azure_image_deployment.strip())


async def _parse_generation_json(
    log: logging.Logger,
    client: httpx.AsyncClient,
    data: dict[str, Any],
) -> ImageGenResult:
    err_msg = _error_from_api_json(data)
    if err_msg:
        log.warning("images_generations_response_error_field: %s", data.get("error"))
        return ImageGenResult(None, err_msg)

    data_list = data.get("data") or []
    if not data_list:
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        log.warning("images_generations_empty_data_keys=%s", keys)
        return ImageGenResult(None, f"API returned empty data (keys={keys}).")

    row = data_list[0] if isinstance(data_list[0], dict) else {}
    b64_raw = row.get("b64_json")
    if b64_raw:
        return ImageGenResult(str(b64_raw), None)
    img_url = row.get("url")
    if isinstance(img_url, str) and img_url.strip():
        log.info("image_gen_using_url_fallback")
        b64_fb = await _async_fetch_image_url_as_b64(client, img_url.strip())
        if b64_fb:
            return ImageGenResult(b64_fb, None)
        return ImageGenResult(None, "Image URL returned but download failed.")

    keys = list(row.keys()) if isinstance(row, dict) else row
    log.warning("images_generations_no_b64_or_url row_keys=%s", keys)
    return ImageGenResult(None, f"No b64_json or url in API row (keys={keys}).")


def parse_minimax_image_payload(data: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Parse MiniMax `image_generation` JSON: (base64_image, error_detail, first_image_url_if_any)."""
    log = logging.getLogger(__name__)
    if not isinstance(data, dict):
        return None, "MiniMax: response is not a JSON object.", None
    base_resp = data.get("base_resp")
    if isinstance(base_resp, dict):
        code = base_resp.get("status_code")
        msg = str(base_resp.get("status_msg") or "").strip()
        if code not in (0, None):
            detail = _safe_detail(f"MiniMax {code}: {msg}") if msg else _safe_detail(f"MiniMax error {code}")
            return None, detail or f"MiniMax error {code}", None
    block = data.get("data")
    if not isinstance(block, dict):
        log.warning("minimax_missing_data_block keys=%s", list(data.keys())[:12])
        return None, "MiniMax: missing data object in response.", None
    b64_list = block.get("image_base64")
    if isinstance(b64_list, list):
        for item in b64_list:
            if isinstance(item, str) and item.strip():
                return item.strip(), None, None
    urls = block.get("image_urls")
    if isinstance(urls, list) and urls and isinstance(urls[0], str) and urls[0].strip():
        return None, None, urls[0].strip()
    return None, "MiniMax: no image_base64 or image_urls in response.", None


async def _generate_via_minimax(scene_prompt: str) -> ImageGenResult:
    """MiniMax image-01 text-to-image (official REST)."""
    log = logging.getLogger(__name__)
    key = settings.minimax_api_key.strip()
    base = settings.minimax_api_base.strip().rstrip("/") or "https://api.minimax.io"
    if not key:
        return ImageGenResult(None, "Missing MiniMax API key (MINIMAX_API_KEY).")

    url = f"{base}/v1/image_generation"
    prompt = _full_image_prompt(scene_prompt, max_total=MINIMAX_PROMPT_MAX)
    model = settings.minimax_image_model.strip() or "image-01"
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "response_format": "base64",
        "aspect_ratio": "1:1",
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
        except httpx.RequestError as e:
            log.warning("minimax_network_error: %s", e)
            return ImageGenResult(None, _safe_detail(str(e)) or "MiniMax network error.")

        if resp.status_code >= 400:
            detail = _error_from_http_body(resp.status_code, resp.text or "")
            log.warning("minimax_http_%s: %s", resp.status_code, (resp.text or "")[:600])
            return ImageGenResult(None, detail or f"MiniMax HTTP {resp.status_code}")

        try:
            data = resp.json()
        except Exception as e:
            log.warning("minimax_json_error: %s body_prefix=%s", e, (resp.text or "")[:400])
            return ImageGenResult(None, "MiniMax: invalid JSON response.")

        if not isinstance(data, dict):
            return ImageGenResult(None, "MiniMax: unexpected JSON shape.")

        b64, err, fetch_url = parse_minimax_image_payload(data)
        if b64:
            return ImageGenResult(b64, None)
        if err:
            return ImageGenResult(None, err)
        if fetch_url:
            b64_fb = await _async_fetch_image_url_as_b64(client, fetch_url)
            if b64_fb:
                log.info("minimax_image_gen_using_url_fallback")
                return ImageGenResult(b64_fb, None)
            return ImageGenResult(None, "MiniMax: image URL returned but download failed.")

        return ImageGenResult(None, "MiniMax image generation failed.")


async def _generate_via_http(scene_prompt: str) -> ImageGenResult:
    log = logging.getLogger(__name__)
    api_key = settings.openai_api_key.strip()
    endpoint = settings.openai_images_endpoint.strip()
    if not endpoint or not api_key:
        return ImageGenResult(None, "Missing OPENAI images endpoint or API key.")

    url = f"{endpoint.rstrip('/')}/images/generations"
    if settings.openai_images_api_version:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api-version={settings.openai_images_api_version}"

    # Deployment-style URLs (Azure / APIM) need api-key even if chat uses bearer-only config.
    auth = (settings.openai_auth_style or "bearer").lower()
    if "/openai/deployments/" in endpoint.lower():
        auth = "azure"
    if auth == "azure":
        headers = _azure_style_headers(settings.openai_api_key)
        base_body_azure: dict[str, Any] = {
            "prompt": _full_image_prompt(scene_prompt),
            "size": "1024x1024",
            "n": 1,
            "quality": "standard",
        }
    else:
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        base_body_azure = {}  # unused

    variants: tuple[dict[str, Any], ...]
    if auth == "azure":
        b1 = dict(base_body_azure)
        b1["response_format"] = "b64_json"
        b2 = dict(base_body_azure)
        variants = (b1, b2)
    else:
        variants = (
            {
                "model": "dall-e-3",
                "prompt": _full_image_prompt(scene_prompt),
                "size": "1024x1024",
                "n": 1,
                "response_format": "b64_json",
            },
            {
                "model": "dall-e-3",
                "prompt": _full_image_prompt(scene_prompt),
                "size": "1024x1024",
                "n": 1,
            },
        )

    last_detail: str | None = None
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        for attempt, body in enumerate(variants):
            try:
                resp = await client.post(url, headers=headers, json=body)
            except httpx.RequestError as e:
                log.warning("images_generations_network_error: %s", e)
                return ImageGenResult(None, _safe_detail(str(e)) or "Network error calling image API.")

            if resp.status_code >= 400:
                detail = _error_from_http_body(resp.status_code, resp.text or "")
                log.warning(
                    "images_generations_http_%s (attempt %s): %s",
                    resp.status_code,
                    attempt,
                    (resp.text or "")[:800],
                )
                last_detail = detail or last_detail
                if resp.status_code in (401, 403):
                    return ImageGenResult(None, last_detail)
                continue

            try:
                data = resp.json()
            except Exception as e:
                log.warning(
                    "images_generations_json_parse_error: %s body_prefix=%s",
                    e,
                    (resp.text or "")[:400],
                )
                return ImageGenResult(None, "Invalid JSON from image API.")

            if not isinstance(data, dict):
                return ImageGenResult(None, "Unexpected image API response shape.")

            parsed = await _parse_generation_json(log, client, data)
            if parsed.b64:
                return parsed
            last_detail = parsed.detail or last_detail
            continue

    return ImageGenResult(None, last_detail or "Image generation failed.")


async def generate_outcome_image(scene_prompt: str) -> ImageGenResult:
    """Generate polaroid art via MiniMax or DALL·E (Azure / OpenAI), depending on `image_provider`."""
    if settings.image_provider == "minimax":
        return await _generate_via_minimax(scene_prompt)

    log = logging.getLogger(__name__)
    api_key = settings.openai_api_key.strip()
    gateway = _azure_gateway_base()

    last: ImageGenResult | None = None
    try_sdk_first = bool(settings.openai_images_use_azure_sdk and gateway and api_key)

    if try_sdk_first:
        sdk = await asyncio.to_thread(generate_outcome_image_sdk_sync, scene_prompt)
        if sdk.b64:
            return sdk
        last = sdk
        log.info("image_gen_azure_sdk_failed_trying_http")

    http = await _generate_via_http(scene_prompt)
    if http.b64:
        return http

    if not try_sdk_first and gateway and api_key:
        log.info("image_gen_http_failed_trying_azure_sdk")
        sdk = await asyncio.to_thread(generate_outcome_image_sdk_sync, scene_prompt)
        if sdk.b64:
            return sdk
        if sdk.detail:
            return ImageGenResult(None, f"{http.detail or 'HTTP failed'}; SDK: {sdk.detail}")
        last = sdk

    if http.detail:
        return http
    if last and last.detail:
        return last
    return ImageGenResult(None, "Image generation produced no output.")