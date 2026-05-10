"""Merge static [`shared/scenarios.json`] data with per-session LLM outline + lazy MC bundles."""

from __future__ import annotations

import logging

from app.game_engine import SessionState
from app.scenarios import ScenarioDef, TurnDef, get_scenario


def effective_scenario(state: SessionState) -> ScenarioDef:
    """Return the scenario view the engine should use (static JSON or dynamic outline + choices)."""
    if getattr(state, "scenario_mode", "static") != "dynamic" or not state.dynamic_outline:
        s = get_scenario(state.scenario_slug)
        if s is None:
            raise ValueError("unknown_scenario")
        return s
    o = state.dynamic_outline
    try:
        title = str(o.get("title") or "").strip() or state.scenario_slug
        tagline = str(o.get("tagline") or "").strip()
        body = str(o.get("body") or "").strip()
        icon = str(o.get("icon") or "⚡").strip()[:8] or "⚡"
        raw_turns = o.get("turns")
        if not isinstance(raw_turns, list) or not raw_turns:
            raise ValueError("dynamic_outline missing turns")
        turns_out: list[TurnDef] = []
        for i, row in enumerate(raw_turns):
            if isinstance(row, dict):
                sl = row.get("static_line")
                static_line = str(sl).strip() if sl is not None else None
            else:
                static_line = None
            pack = state.choices_by_turn.get(i) if hasattr(state, "choices_by_turn") else None
            if isinstance(pack, dict):
                ch = list(pack.get("choices") or [])
                sd = [int(x) for x in (pack.get("score_delta_by_choice") or [])]
            else:
                ch, sd = [], []
            turns_out.append(
                TurnDef(
                    id=i,
                    choices=ch,
                    score_delta_by_choice=sd,
                    static_line=static_line or None,
                )
            )
        return ScenarioDef(
            slug=state.scenario_slug,
            title=title,
            icon=icon,
            tagline=tagline,
            body=body,
            turns=turns_out,
        )
    except Exception as e:
        logging.getLogger(__name__).warning("effective_scenario_dynamic_fallback: %s", e)
        s = get_scenario(state.scenario_slug)
        if s is None:
            raise ValueError("unknown_scenario") from e
        return s


def narrator_history_snippet(state: SessionState, max_chars: int = 800) -> str:
    """Short concatenation of recent narrator lines for turn-choice conditioning."""
    parts: list[str] = []
    for m in reversed(state.messages):
        if m.get("role") != "narrator":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            parts.append(c.strip())
        if len(parts) >= 3:
            break
    text = " ".join(reversed(parts))
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text
