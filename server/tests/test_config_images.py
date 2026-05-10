"""Azure env aliases for image generation (independent of chat deployment)."""

from app.config import Settings


def test_image_endpoint_and_auth_when_only_image_deployment(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://hkust.azure-api.net")
    monkeypatch.setenv("AZURE_IMAGE_DEPLOYMENT", "dall-e-3")
    # Override any value from `.env` so chat deployment is absent for this assertion.
    monkeypatch.setenv("AZURE_DEPLOYMENT_NAME", "")

    s = Settings()
    assert s.openai_api_key == "test-key"
    assert s.openai_images_endpoint == "https://hkust.azure-api.net/openai/deployments/dall-e-3"
    # Chat stays on default bearer + public base until AZURE_DEPLOYMENT_NAME is set.
    assert s.openai_auth_style == "bearer"
