from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from app.scenarios import ScenarioDef, get_scenario, load_scenarios

# Points lost when the player asks for AI-generated multiple-choice options.
AI_OPTIONS_PENALTY = 8

AnswerMode = Literal["free_text", "ai_options"]


class Phase(str, Enum):
    awaiting_answer_mode = "awaiting_answer_mode"
    awaiting_choice = "awaiting_choice"
    streaming = "streaming"
    ended = "ended"


@dataclass
class SessionState:
    session_id: str
    scenario_slug: str
    phase: Phase = Phase.awaiting_answer_mode
    turn_index: int = 0
    neural_score: int = 50
    answer_mode: AnswerMode | None = None
    last_choice_index: int | None = None
    narrative_buffer: str = ""
    achievement_unlocked: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    neurobot_history: list[dict[str, str]] = field(default_factory=list)
    outcome_image_b64: str | None = None
    outcome_image_status: str = "idle"
    scenario_art_b64: str | None = None
    scenario_art_status: str = "idle"


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def create(self, scenario_slug: str) -> SessionState:
        if get_scenario(scenario_slug) is None:
            raise ValueError("unknown_scenario")
        sid = str(uuid.uuid4())
        st = SessionState(session_id=sid, scenario_slug=scenario_slug)
        self._sessions[sid] = st
        self._locks[sid] = asyncio.Lock()
        return st

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def lock_for(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())


store = SessionStore()


def apply_answer_mode(state: SessionState, scenario: ScenarioDef, mode: str) -> dict[str, Any]:
    """Lock in free-text vs AI-options play style for the session; applies penalty for AI options."""
    if state.phase != Phase.awaiting_answer_mode:
        raise ValueError("not_awaiting_answer_mode")
    if mode not in ("free_text", "ai_options"):
        raise ValueError("bad_answer_mode")
    state.answer_mode = mode  # type: ignore[assignment]
    if mode == "ai_options":
        state.neural_score = max(0, min(100, state.neural_score - AI_OPTIONS_PENALTY))
    state.phase = Phase.awaiting_choice
    state.neurobot_history.clear()
    state.outcome_image_b64 = None
    state.outcome_image_status = "idle"
    turn = scenario.turns[state.turn_index]
    out: dict[str, Any] = {
        "phase": state.phase.value,
        "answer_mode": state.answer_mode,
        "neural_score": state.neural_score,
        "turn_index": state.turn_index,
        "choices": turn.choices if mode == "ai_options" else [],
        "static_line": turn.static_line,
    }
    if mode == "ai_options":
        out["ai_options_penalty"] = AI_OPTIONS_PENALTY
    return out


def parse_score_change_line(narrative: str) -> tuple[str, int]:
    """Strip trailing SCORE_CHANGE: <int> from model output; return cleaned text and delta."""
    text = narrative.strip()
    m = re.search(r"SCORE_CHANGE:\s*([+-]?\d+)\s*$", text, re.MULTILINE)
    if not m:
        return text, 0
    delta = max(-15, min(15, int(m.group(1))))
    cleaned = text[: m.start()].strip()
    return cleaned, delta


def apply_choice(state: SessionState, scenario: ScenarioDef, choice_index: int) -> dict[str, Any]:
    if state.answer_mode != "ai_options":
        raise ValueError("wrong_answer_mode")
    turn = scenario.turns[state.turn_index]
    if choice_index < 0 or choice_index >= len(turn.choices):
        raise ValueError("bad_choice")
    delta = turn.score_delta_by_choice[choice_index]
    state.neural_score = max(0, min(100, state.neural_score + delta))
    state.last_choice_index = choice_index
    state.neurobot_history.clear()
    state.outcome_image_b64 = None
    state.outcome_image_status = "idle"
    choice_label = turn.choices[choice_index]
    state.messages.append(
        {"role": "player", "turn": state.turn_index, "choice": choice_label, "score_delta": delta}
    )
    return {"choice_label": choice_label, "score_delta": delta}


def apply_free_text(state: SessionState, scenario: ScenarioDef, text: str) -> None:
    if state.answer_mode != "free_text":
        raise ValueError("wrong_answer_mode")
    turn = scenario.turns[state.turn_index]
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty_text")
    if len(cleaned) > 2000:
        raise ValueError("text_too_long")
    state.last_choice_index = None
    state.neurobot_history.clear()
    state.outcome_image_b64 = None
    state.outcome_image_status = "idle"
    state.messages.append(
        {
            "role": "player",
            "turn": state.turn_index,
            "free_text": cleaned,
        }
    )


def build_ai_messages(scenario: ScenarioDef, state: SessionState) -> list[dict[str, str]]:
    turn = scenario.turns[state.turn_index]
    last_player: dict[str, Any] | None = None
    for m in reversed(state.messages):
        if m.get("role") == "player":
            last_player = m
            break
    last_free: str | None = None
    choice_line = ""
    if last_player is not None:
        if "free_text" in last_player:
            last_free = str(last_player["free_text"])
        elif "choice" in last_player:
            choice_line = str(last_player["choice"])
    system = (
        "You are the narrator of a short satirical office game about AI dysfunction. "
        "Stay in voice: witty, slightly bleak, under four sentences. "
        "Do not give numbered choices or meta instructions."
    )
    user_parts = [
        f"Scenario: {scenario.title} — {scenario.tagline}",
        f"Turn {state.turn_index + 1} of {len(scenario.turns)}.",
    ]
    if turn.static_line:
        user_parts.append(f"Scene setup for this turn: {turn.static_line}")
    if last_free is not None:
        user_parts.append(f"The player typed into NeuroBot: {last_free}")
        user_parts.append(
            "React in 2-4 short sentences as the narrator. "
            "On the very last line by itself, output exactly: SCORE_CHANGE: <integer from -15 to +15> "
            "where positive means their answer helped their neural score (wisdom, caution, ethics) "
            "and negative means it made things worse."
        )
    elif choice_line:
        user_parts.append(f"The player chose: {choice_line}")
        user_parts.append("Describe what happens next.")
    else:
        user_parts.append("Describe what happens next.")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def advance_after_stream(state: SessionState, scenario: ScenarioDef, narrative: str) -> dict[str, Any]:
    display_narrative = narrative
    last_player: dict[str, Any] | None = None
    for m in reversed(state.messages):
        if m.get("role") == "player":
            last_player = m
            break
    if (
        last_player is not None
        and "free_text" in last_player
        and int(last_player["turn"]) == state.turn_index
    ):
        display_narrative, fdelta = parse_score_change_line(narrative)
        state.neural_score = max(0, min(100, state.neural_score + fdelta))

    state.messages.append({"role": "narrator", "turn": state.turn_index, "content": display_narrative})
    state.turn_index += 1
    state.narrative_buffer = ""
    patch: dict[str, Any] = {"neural_score": state.neural_score, "turn_index": state.turn_index}

    if state.turn_index >= len(scenario.turns):
        state.phase = Phase.ended
        raw, _ = load_scenarios()
        ach_stub = raw.get("vertical_slice", {}).get("achievement_stub_id")
        if ach_stub and state.neural_score >= 40:
            state.achievement_unlocked = ach_stub
            patch["achievement_unlocked"] = ach_stub
        patch["ended"] = True
        patch["choices"] = []
        patch["static_line"] = None
    else:
        state.phase = Phase.awaiting_choice
        next_turn = scenario.turns[state.turn_index]
        if state.answer_mode == "ai_options":
            patch["choices"] = next_turn.choices
        else:
            patch["choices"] = []
        patch["static_line"] = next_turn.static_line

    return patch


def initial_client_snapshot(state: SessionState, scenario: ScenarioDef) -> dict[str, Any]:
    turn0 = scenario.turns[0]
    return {
        "session_id": state.session_id,
        "scenario": {
            "slug": scenario.slug,
            "title": scenario.title,
            "icon": scenario.icon,
            "tagline": scenario.tagline,
            "body": scenario.body,
        },
        "phase": state.phase.value,
        "turn_index": state.turn_index,
        "neural_score": state.neural_score,
        "answer_mode": state.answer_mode,
        "choices": [],
        "static_line": turn0.static_line,
        "scenario_art_status": state.scenario_art_status,
        "scenario_art_b64": state.scenario_art_b64,
    }


def sse_encode(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
