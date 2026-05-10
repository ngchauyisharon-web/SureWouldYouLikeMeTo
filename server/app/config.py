from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    # When True, call DALL·E via AzureOpenAI SDK (HKUST gateway) instead of raw HTTP.
    openai_images_use_azure_sdk: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Colab / HKUST-style aliases (optional). Mapped in apply_azure_env_aliases.
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_deployment_name: str = ""
    azure_embedding_deployment: str = ""
    azure_image_deployment: str = ""

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

        # HKUST / Azure APIM expects api-key header for both chat and images HTTP calls.
        if ep and (dep or img):
            self.openai_auth_style = "azure"
            if not self.openai_api_version.strip():
                self.openai_api_version = "2025-02-01-preview"

        if ep and dep:
            base = self.openai_base_url.strip()
            if not base or base == _DEFAULT_PUBLIC_OPENAI_BASE:
                self.openai_base_url = f"{ep}/openai/deployments/{dep}"

            # Keep model label aligned with chat deployment (used for non-Azure paths / docs).
            if self.openai_model.strip() in ("", "gpt-4o-mini"):
                self.openai_model = dep

        return self


settings = Settings()
