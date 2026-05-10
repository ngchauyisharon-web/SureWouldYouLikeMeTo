"""LLM-backed scenario outline (session start) and per-turn MC options (lazy)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai_provider import chat_completion_text
from app.dynamic_scenario import narrator_history_snippet
from app.game_engine import SessionState
from app.scenarios import ScenarioDef


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


class OutlineTurn(BaseModel):
    static_line: str = Field(..., min_length=1, max_length=600)


class ScenarioOutline(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    tagline: str = Field(..., max_length=400)
    body: str = Field(..., max_length=1200)
    icon: str = Field(default="⚡", max_length=8)
    turns: list[OutlineTurn] = Field(..., min_length=1, max_length=12)

    @field_validator("turns")
    @classmethod
    def reasonable_turn_count(cls, v: list[OutlineTurn]) -> list[OutlineTurn]:
        if len(v) > 12:
            return v[:12]
        return v


class TurnChoicesPayload(BaseModel):
    choices: list[str]
    score_delta_by_choice: list[int]

    @field_validator("choices")
    @classmethod
    def four_nonempty(cls, v: list[str]) -> list[str]:
        if len(v) != 4:
            raise ValueError("expected exactly 4 choices")
        out = [str(x).strip()[:220] for x in v]
        if any(not s for s in out):
            raise ValueError("empty choice")
        return out

    @field_validator("score_delta_by_choice")
    @classmethod
    def four_deltas(cls, v: list[int]) -> list[int]:
        if len(v) != 4:
            raise ValueError("expected exactly 4 score deltas")
        return [max(-15, min(15, int(x))) for x in v]


def _fit_turns(theme: ScenarioDef, rows: list[OutlineTurn]) -> list[OutlineTurn]:
    n = len(theme.turns)
    out = list(rows[:n])
    while len(out) < n:
        t = theme.turns[len(out)]
        fallback = (t.static_line or t.choices[0] if t.choices else theme.tagline) or theme.body
        out.append(OutlineTurn(static_line=str(fallback)[:600]))
    return out[:n]


async def generate_scenario_outline(theme: ScenarioDef) -> dict[str, Any]:
    """Produce validated outline dict (title, tagline, body, icon, turns with static_line)."""
    n = len(theme.turns)
    sys = (
        "You write concise JSON for a short satirical office game about AI dysfunction. "
        "Output ONLY a single JSON object, no markdown, no commentary."
    )
    user = (
        f"Theme seed (loose inspiration; invent a fresh scenario in the same vibe):\n"
        f"Title: {theme.title}\nTagline: {theme.tagline}\nBody: {theme.body}\n\n"
        f'Required JSON shape: {{"title": string, "tagline": string, "body": string, "icon": string, '
        f'"turns": [{{"static_line": string}}, ...]}}\n'
        f"- Exactly {n} objects in \"turns\".\n"
        f"- Each static_line: one vivid dilemma moment (1-3 sentences). No numbered lists inside static_line.\n"
        f"- icon: a single emoji.\n"
        f"- title/tagline/body: new scenario copy, not copies of the seed.\n"
    )
    raw = await chat_completion_text(
        [{"role": "system", "content": sys}, {"role": "user", "content": user}],
        max_tokens=1800,
        temperature=0.85,
    )
    data = _extract_json_object(raw)
    outline = ScenarioOutline.model_validate(data)
    fitted = _fit_turns(theme, outline.turns)
    return {
        "title": outline.title,
        "tagline": outline.tagline,
        "body": outline.body,
        "icon": outline.icon,
        "turns": [{"static_line": t.static_line} for t in fitted],
    }


async def generate_turn_choices_bundle(
    *,
    outline: dict[str, Any],
    turn_index: int,
    history_summary: str,
) -> TurnChoicesPayload:
    turns = outline.get("turns") or []
    if not isinstance(turns, list) or turn_index < 0 or turn_index >= len(turns):
        raise ValueError("bad_turn_index")
    row = turns[turn_index]
    static_line = str(row.get("static_line", "")).strip() if isinstance(row, dict) else ""
    title = str(outline.get("title", ""))
    tagline = str(outline.get("tagline", ""))
    sys = (
        "You write JSON only for a satirical office game's multiple-choice beat. "
        "Four distinct actions; score_delta_by_choice[i] is neural impact for choices[i] "
        "(roughly -12 bad to +10 good)."
    )
    hist = (history_summary or "").strip()
    hist_part = f"\nStory so far (may be empty):\n{hist}\n" if hist else ""
    user = (
        f"Scenario: {title} — {tagline}\n"
        f"Turn {turn_index + 1} dilemma:\n{static_line}\n"
        f"{hist_part}\n"
        f'Return ONLY JSON: {{"choices": [string, string, string, string], '
        f'"score_delta_by_choice": [int, int, int, int]}}\n'
        f"- choices: short imperative or dialog-ish lines, under 120 chars each, no numbering prefix.\n"
    )
    raw = await chat_completion_text(
        [{"role": "system", "content": sys}, {"role": "user", "content": user}],
        max_tokens=500,
        temperature=0.75,
    )
    data = _extract_json_object(raw)
    return TurnChoicesPayload.model_validate(data)


async def ensure_choices_for_turn(state: SessionState, turn_index: int) -> None:
    """Populate state.choices_by_turn[turn_index] for dynamic + ai_options (mutates state)."""
    if state.scenario_mode != "dynamic" or not state.dynamic_outline:
        return
    existing = state.choices_by_turn.get(turn_index)
    if isinstance(existing, dict) and len(existing.get("choices") or []) == 4:
        return
    state.turn_generation_error = None
    try:
        bundle = await generate_turn_choices_bundle(
            outline=state.dynamic_outline,
            turn_index=turn_index,
            history_summary=narrator_history_snippet(state),
        )
        state.choices_by_turn[turn_index] = {
            "choices": bundle.choices,
            "score_delta_by_choice": bundle.score_delta_by_choice,
        }
    except Exception as e:
        logging.getLogger(__name__).warning("ensure_choices_for_turn: %s", e)
        state.turn_generation_error = str(e).replace("\n", " ")[:280]
        state.choices_by_turn[turn_index] = {"choices": [], "score_delta_by_choice": []}
