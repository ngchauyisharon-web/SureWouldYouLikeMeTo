from __future__ import annotations

import os
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bootstrap_azure_env_from_colab_defaults() -> None:
    """Match Colab `os.environ.setdefault` for HKUST (non-secrets only — put AZURE_OPENAI_API_KEY in `.env`)."""
    os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://hkust.azure-api.net")
    os.environ.setdefault("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")
    os.environ.setdefault("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    os.environ.setdefault("AZURE_IMAGE_DEPLOYMENT", "dall-e-3")


_bootstrap_azure_env_from_colab_defaults()

_DEFAULT_PUBLIC_OPENAI_BASE = "https://api.openai.com/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = _DEFAULT_PUBLIC_OPENAI_BASE
    openai_model: str = "gpt-4o-mini"
    openai_auth_style: str = "bearer"  # bearer | azure
    openai_api_version: str = ""
    openai_images_endpoint: str = ""
    openai_images_api_version: str = "2025-02-01-preview"
    # When True, call DALL·E via Azure OpenAI SDK (HKUST APIM) first; HTTP is fallback.
    openai_images_use_azure_sdk: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Colab / HKUST-style aliases (optional). Mapped in apply_azure_env_aliases.
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_deployment_name: str = ""
    azure_embedding_deployment: str = ""
    azure_image_deployment: str = ""

    # Image provider: "openai" = DALL·E / Azure images; "minimax" = MiniMax image-01 (requires MINIMAX_API_KEY).
    image_provider: Literal["openai", "minimax"] = "openai"
    minimax_api_key: str = ""
    minimax_api_base: str = "https://api.minimax.io"
    minimax_image_model: str = "image-01"
    # Optional extra style phrase appended to image prompts (e.g. trademarked look if your gateway allows).
    image_style_label: str = ""

    @field_validator("image_provider", mode="before")
    @classmethod
    def _norm_image_provider(cls, v: object) -> str:
        s = str(v or "openai").strip().lower()
        if s in ("openai", "minimax"):
            return s
        return "openai"

    @model_validator(mode="after")
    def apply_azure_env_aliases(self):
        """Support AZURE_OPENAI_* env vars like the Colab notebook."""
        ak = self.azure_openai_api_key.strip()
        if ak and not self.openai_api_key.strip():
            self.openai_api_key = ak

        ep = self.azure_openai_endpoint.strip().rstrip("/")
        dep = self.azure_deployment_name.strip()
        img = self.azure_image_deployment.strip()

        # DALL·E deployment URL — must not depend on chat AZURE_DEPLOYMENT_NAME being set.
        if ep and img and not self.openai_images_endpoint.strip():
            self.openai_images_endpoint = f"{ep}/openai/deployments/{img}"

        # Chat completions: only switch to Azure api-key + api-version when a chat deployment exists.
        # (Image-only AZURE_IMAGE_DEPLOYMENT must not force chat onto api.openai.com with api-key.)
        if ep and dep:
            self.openai_auth_style = "azure"
            if not self.openai_api_version.strip():
                self.openai_api_version = "2025-02-01-preview"
            base = self.openai_base_url.strip()
            if not base or base == _DEFAULT_PUBLIC_OPENAI_BASE:
                self.openai_base_url = f"{ep}/openai/deployments/{dep}"
            # Keep model label aligned with chat deployment (used for non-Azure paths / docs).
            if self.openai_model.strip() in ("", "gpt-4o-mini"):
                self.openai_model = dep

        return self


settings = Settings()
