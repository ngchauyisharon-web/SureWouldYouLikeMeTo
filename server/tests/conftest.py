"""Pytest fixtures shared across server tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_narrator_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use offline narrator tokens instead of live chat completions (stable in CI and with depleted credits)."""
    from app import ai_provider

    monkeypatch.setattr("app.main.stream_chat_completion", ai_provider._mock_stream)


@pytest.fixture
def mock_neurobot_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid live NeuroBot coach HTTP when an API key is present but unusable."""

    async def _fixed_reply(_messages: list[dict[str, str]], **_kwargs: object) -> str:
        return "Offline coach: watch incentives and who owns the downside."

    monkeypatch.setattr("app.neurobot_coach.chat_completion_text", _fixed_reply)
