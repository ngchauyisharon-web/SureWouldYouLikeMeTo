"""build_post_choice_scene_prompt — outcome polaroid text."""

from app.image_gen import build_post_choice_scene_prompt


def test_post_choice_includes_choice_and_narrative() -> None:
    s = build_post_choice_scene_prompt(
        scenario_title="AI Overuse",
        completed_turn_index=0,
        total_turns=3,
        choice_label="Ship it anyway",
        free_text_excerpt=None,
        narrative_display="The slide deck ignites. Metrics stay green.",
    )
    assert "AI Overuse" in s
    assert "Ship it anyway" in s
    assert "slide deck ignites" in s.lower()
    assert "After turn 1 of 3" in s


def test_post_choice_free_text_truncates_long_input() -> None:
    long_ft = "word " * 80
    s = build_post_choice_scene_prompt(
        scenario_title="X",
        completed_turn_index=1,
        total_turns=3,
        choice_label=None,
        free_text_excerpt=long_ft,
        narrative_display="Done.",
    )
    assert "Player said:" in s
    assert len(s) <= 600
    assert s.endswith("…") or "word word" in s


def test_post_choice_narrative_truncation() -> None:
    long_n = "x" * 700
    s = build_post_choice_scene_prompt(
        scenario_title="Y",
        completed_turn_index=0,
        total_turns=2,
        choice_label="Opt A",
        free_text_excerpt=None,
        narrative_display=long_n,
    )
    assert len(s) <= 600
    assert "What happened next" in s


def test_post_choice_narrative_only_if_missing_action() -> None:
    s = build_post_choice_scene_prompt(
        scenario_title="Z",
        completed_turn_index=0,
        total_turns=1,
        choice_label=None,
        free_text_excerpt=None,
        narrative_display="Only outcome text.",
    )
    assert "What happened next" in s
    assert "Only outcome" in s
