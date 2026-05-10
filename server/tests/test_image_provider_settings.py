"""Settings: image provider and MiniMax fields."""

import os

import pytest

from app.config import Settings


def test_image_provider_defaults_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    s = Settings()
    assert s.image_provider == "openai"


def test_image_provider_minimax_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAGE_PROVIDER", "MiniMax")
    monkeypatch.setenv("MINIMAX_API_KEY", "k")
    s = Settings()
    assert s.image_provider == "minimax"


def test_invalid_image_provider_falls_back_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAGE_PROVIDER", "flux")
    s = Settings()
    assert s.image_provider == "openai"
