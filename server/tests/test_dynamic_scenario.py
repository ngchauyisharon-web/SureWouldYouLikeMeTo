"""Resolver + outline helpers."""

from __future__ import annotations

from app.dynamic_scenario import effective_scenario, narrator_history_snippet
from app.game_engine import SessionState
from app.scenario_generation import OutlineTurn, _fit_turns
from app.scenarios import get_scenario


def test_effective_static_matches_json() -> None:
    st = SessionState(session_id="test-sid", scenario_slug="ai_overuse")
    s = effective_scenario(st)
    assert s.slug == "ai_overuse"
    assert len(s.turns) == len(get_scenario("ai_overuse").turns)


def test_effective_dynamic_merges_choices() -> None:
    st = SessionState(session_id="sid", scenario_slug="ai_overuse")
    st.scenario_mode = "dynamic"
    st.dynamic_outline = {
        "title": "Dyn Title",
        "tagline": "Dyn tag",
        "body": "Dyn body",
        "icon": "🤖",
        "turns": [{"static_line": "First dilemma."}, {"static_line": "Second dilemma."}],
    }
    st.choices_by_turn[0] = {
        "choices": ["A", "B", "C", "D"],
        "score_delta_by_choice": [1, -2, 3, -4],
    }
    s = effective_scenario(st)
    assert s.title == "Dyn Title"
    assert len(s.turns) == 2
    assert s.turns[0].choices == ["A", "B", "C", "D"]
    assert s.turns[0].score_delta_by_choice == [1, -2, 3, -4]
    assert s.turns[1].choices == []


def test_narrator_history_snippet_truncates() -> None:
    st = SessionState(session_id="x", scenario_slug="ai_overuse")
    st.messages.append({"role": "narrator", "turn": 0, "content": "x" * 500})
    h = narrator_history_snippet(st, max_chars=100)
    assert len(h) <= 101


def test_fit_turns_pads_to_theme_length() -> None:
    theme = get_scenario("ai_overuse")
    assert theme is not None
    short = [OutlineTurn(static_line="only one")]
    fitted = _fit_turns(theme, short)
    assert len(fitted) == len(theme.turns)
