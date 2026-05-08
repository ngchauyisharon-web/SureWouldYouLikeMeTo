from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.scenarios import ScenarioDef, get_scenario, load_scenarios


class Phase(str, Enum):
    awaiting_choice = "awaiting_choice"
    streaming = "streaming"
    ended = "ended"


@dataclass
class SessionState:
    session_id: str
    scenario_slug: str
    phase: Phase = Phase.awaiting_choice
    turn_index: int = 0
    neural_score: int = 50
    last_choice_index: int | None = None
    narrative_buffer: str = ""
    achievement_unlocked: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)


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


def apply_choice(state: SessionState, scenario: ScenarioDef, choice_index: int) -> dict[str, Any]:
    turn = scenario.turns[state.turn_index]
    if choice_index < 0 or choice_index >= len(turn.choices):
        raise ValueError("bad_choice")
    delta = turn.score_delta_by_choice[choice_index]
    state.neural_score = max(0, min(100, state.neural_score + delta))
    state.last_choice_index = choice_index
    choice_label = turn.choices[choice_index]
    state.messages.append(
        {"role": "player", "turn": state.turn_index, "choice": choice_label, "score_delta": delta}
    )
    return {"choice_label": choice_label, "score_delta": delta}


def build_ai_messages(scenario: ScenarioDef, state: SessionState) -> list[dict[str, str]]:
    turn = scenario.turns[state.turn_index]
    choice_line = ""
    if state.last_choice_index is not None:
        choice_line = turn.choices[state.last_choice_index]
    system = (
        "You are the narrator of a short satirical office game about AI dysfunction. "
        "Stay in voice: witty, slightly bleak, under four sentences. "
        "Do not give numbered choices or meta instructions."
    )
    user_parts = [
        f"Scenario: {scenario.title} — {scenario.tagline}",
        f"Turn {state.turn_index + 1} of {len(scenario.turns)}.",
    ]
    if turn.static_line and state.last_choice_index is None:
        user_parts.append(f"Opening beat (already shown to player): {turn.static_line}")
    if choice_line:
        user_parts.append(f"The player chose: {choice_line}")
    user_parts.append("Describe what happens next.")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def advance_after_stream(state: SessionState, scenario: ScenarioDef, narrative: str) -> dict[str, Any]:
    state.messages.append({"role": "narrator", "turn": state.turn_index, "content": narrative})
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
        patch["choices"] = next_turn.choices
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
        "choices": turn0.choices,
        "static_line": turn0.static_line,
    }


def sse_encode(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
