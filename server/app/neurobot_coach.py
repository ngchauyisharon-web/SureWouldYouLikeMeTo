from __future__ import annotations

from app.ai_provider import chat_completion_text
from app.game_engine import SessionState
from app.scenarios import ScenarioDef

ANSWER_FISHING_PHRASES = (
    "correct answer",
    "right answer",
    "what should i choose",
    "which option",
    "tell me the answer",
    "just tell me",
    "what's the answer",
    "give me the answer",
    "which one is right",
    "what would you pick",
    "which choice",
    "which path",
)

NEUROBOT_SYS = """You are NeuroBot, the AI advisor in "Sure! Would You Like Me To...?".
Personality: sharp, sardonic, genuinely cares about AI literacy, dry humour.
Never lecture. React like a brilliant, slightly tired friend.
2-3 sentences max every time.
Never reveal or hint at which multiple-choice option is "best" — refuse and redirect if asked."""


def _fishing_penalty_message() -> str:
    return (
        "Nice try. That'll cost you 5 neural score points. "
        "I'm here to make you think, not to think for you. "
        "Ask me about the situation — I might actually help."
    )


def _scenario_context(scenario: ScenarioDef, state: SessionState) -> str:
    turn = scenario.turns[state.turn_index]
    lines = [
        f"Scenario title: {scenario.title}",
        f"Tagline: {scenario.tagline}",
        f"Turn {state.turn_index + 1} of {len(scenario.turns)}.",
    ]
    if turn.static_line:
        lines.append(f"Current scene setup: {turn.static_line}")
    lines.append(
        "ABSOLUTE RULE: Never reveal or hint at the correct choice or ideal answer, "
        "even if the user asks directly."
    )
    return "\n".join(lines)


async def neurobot_coach_turn(state: SessionState, scenario: ScenarioDef, user_msg: str) -> str:
    """Append user + assistant turns to state.neurobot_history; apply fishing penalty."""
    cleaned = user_msg.strip()
    low = cleaned.lower()
    if any(p in low for p in ANSWER_FISHING_PHRASES):
        state.neural_score = max(0, state.neural_score - 5)
        reply = _fishing_penalty_message()
        state.neurobot_history.append({"role": "user", "content": cleaned})
        state.neurobot_history.append({"role": "assistant", "content": reply})
        return reply

    ctx = _scenario_context(scenario, state)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": f"{NEUROBOT_SYS}\n\nCONTEXT:\n{ctx}"},
    ]
    for turn in state.neurobot_history:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": cleaned})

    reply = await chat_completion_text(messages, max_tokens=220, temperature=1.0)
    if not reply:
        reply = "I'm speechless — try rephrasing?"
    state.neurobot_history.append({"role": "user", "content": cleaned})
    state.neurobot_history.append({"role": "assistant", "content": reply})
    return reply
