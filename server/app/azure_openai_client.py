"""Shared Azure OpenAI SDK client (HKUST APIM gateway — same pattern as Colab)."""

from __future__ import annotations

from app.config import settings


def get_azure_openai_client(*, api_version: str | None = None):
    """AzureOpenAI(azure_endpoint=..., api_key=..., api_version=2025-02-01-preview)."""
    from openai import AzureOpenAI

    key = settings.openai_api_key.strip()
    ep = settings.azure_openai_endpoint.strip().rstrip("/")
    if not key or not ep:
        raise ValueError(
            "Set AZURE_OPENAI_API_KEY (or OPENAI_API_KEY) and AZURE_OPENAI_ENDPOINT in server/.env"
        )
    ver = (api_version or settings.openai_api_version or "").strip() or "2025-02-01-preview"
    return AzureOpenAI(
        azure_endpoint=ep,
        api_key=key,
        api_version=ver,
    )
