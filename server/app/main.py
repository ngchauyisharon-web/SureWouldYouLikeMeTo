from __future__ import annotations

import asyncio
import logging

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.ai_provider import stream_chat_completion
from app.config import settings
from app.dynamic_scenario import effective_scenario
from app.game_engine import (
    Phase,
    advance_after_stream,
    apply_answer_mode,
    apply_choice,
    apply_free_text,
    build_ai_messages,
    initial_client_snapshot,
    parse_score_change_line,
    scenario_art_begin_turn,
    sse_encode,
    store,
)
from app.image_gen import (
    build_post_choice_scene_prompt,
    build_question_turn_prompt,
    generate_outcome_image,
    is_image_generation_configured,
)
from app.neurobot_coach import neurobot_coach_turn
from app.scenario_generation import ensure_choices_for_turn, generate_scenario_outline
from app.scenarios import get_scenario, list_scenario_summaries

app = FastAPI(title="SureWouldYouLikeMeTo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateSessionBody(BaseModel):
    scenario_slug: str = Field(..., examples=["ai_overuse"])
    source: Literal["static", "generated"] = "static"


class ChoiceBody(BaseModel):
    choice_index: int = Field(..., ge=0)


class AnswerModeBody(BaseModel):
    mode: str = Field(..., pattern="^(free_text|ai_options)$")


class FreeTextBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NeuroBotBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)


async def _run_question_art_job(session_id: str, art_turn_index: int, scene_prompt: str) -> None:
    b64: str | None = None
    detail: str | None = None
    try:
        out = await generate_outcome_image(scene_prompt)
        b64 = out.b64
        detail = out.detail
    except Exception as e:
        logging.getLogger(__name__).warning("question_art_job_error: %s", e)
        detail = str(e).replace("\n", " ")[:280]
    lock = store.lock_for(session_id)
    async with lock:
        st = store.get(session_id)
        if st is None or st.turn_index != art_turn_index:
            return
        if b64:
            st.scenario_art_b64 = b64
            st.scenario_art_status = "ready"
            st.scenario_art_detail = None
        else:
            st.scenario_art_status = "failed"
            st.scenario_art_detail = detail
            logging.getLogger(__name__).warning(
                "question_art_job_no_image session_id_prefix=%s detail=%s",
                session_id[:13],
                (detail or "")[:120],
            )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def api_scenarios() -> dict:
    return {"scenarios": list_scenario_summaries()}


@app.post("/api/sessions")
async def create_session(body: CreateSessionBody) -> dict:
    try:
        state = store.create(body.scenario_slug)
    except ValueError:
        raise HTTPException(status_code=400, detail="unknown_scenario") from None
    theme = get_scenario(body.scenario_slug)
    assert theme is not None
    if body.source == "generated":
        try:
            outline = await generate_scenario_outline(theme)
            state.scenario_mode = "dynamic"
            state.dynamic_outline = outline
            state.outline_generation_error = None
        except Exception as e:
            logging.getLogger(__name__).warning("generate_scenario_outline_failed: %s", e)
            state.scenario_mode = "static"
            state.dynamic_outline = None
            state.outline_generation_error = str(e).replace("\n", " ")[:280]
    scenario = effective_scenario(state)
    return initial_client_snapshot(state, scenario)


@app.post("/api/sessions/{session_id}/answer-mode")
async def post_answer_mode(session_id: str, body: AnswerModeBody) -> dict:
    lock = store.lock_for(session_id)
    schedule: tuple[str, int, str] | None = None
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found") from None
        if body.mode == "ai_options" and state.scenario_mode == "dynamic":
            await ensure_choices_for_turn(state, 0)
        scenario = effective_scenario(state)
        try:
            result = apply_answer_mode(state, scenario, body.mode)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        if state.turn_generation_error:
            result["choices_error"] = state.turn_generation_error
        if is_image_generation_configured():
            turn = scenario.turns[state.turn_index]
            scene = build_question_turn_prompt(
                scenario_title=scenario.title,
                tagline=scenario.tagline,
                body=scenario.body,
                static_line=turn.static_line,
                turn_index=state.turn_index,
                total_turns=len(scenario.turns),
            )
            result.update(scenario_art_begin_turn(state))
            schedule = (state.session_id, state.turn_index, scene)
    if schedule:
        sid, tidx, scn = schedule
        asyncio.create_task(_run_question_art_job(sid, tidx, scn))
    return result


@app.post("/api/sessions/{session_id}/free-text")
async def post_free_text(session_id: str, body: FreeTextBody) -> dict:
    lock = store.lock_for(session_id)
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found") from None
        if state.phase != Phase.awaiting_choice:
            raise HTTPException(status_code=400, detail="not_awaiting_choice") from None
        scenario = effective_scenario(state)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario_missing") from None
        try:
            apply_free_text(state, scenario, body.text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        state.phase = Phase.streaming
    return {"ok": True}


@app.post("/api/sessions/{session_id}/choice")
async def submit_choice(session_id: str, body: ChoiceBody) -> dict:
    lock = store.lock_for(session_id)
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found")
        if state.phase != Phase.awaiting_choice:
            raise HTTPException(status_code=400, detail="not_awaiting_choice")
        scenario = effective_scenario(state)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario_missing")
        try:
            apply_choice(state, scenario, body.choice_index)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        state.phase = Phase.streaming
    return {"ok": True}


@app.post("/api/sessions/{session_id}/neurobot-chat")
async def post_neurobot_chat(session_id: str, body: NeuroBotBody) -> dict:
    lock = store.lock_for(session_id)
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found") from None
        if state.phase != Phase.awaiting_choice:
            raise HTTPException(status_code=400, detail="not_investigation_phase") from None
        scenario = effective_scenario(state)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario_missing") from None
        reply = await neurobot_coach_turn(state, scenario, body.message)
        return {"reply": reply, "neural_score": state.neural_score}


@app.get("/api/sessions/{session_id}/outcome-image")
def get_outcome_image(session_id: str) -> dict:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {
        "status": state.outcome_image_status,
        "b64": state.outcome_image_b64,
        "detail": state.outcome_image_detail,
    }


@app.get("/api/sessions/{session_id}/scenario-art")
def get_scenario_art(session_id: str) -> dict:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {
        "status": state.scenario_art_status,
        "b64": state.scenario_art_b64,
        "detail": state.scenario_art_detail,
        "scenario_art_turn_index": state.scenario_art_turn_index,
    }


@app.get("/api/sessions/{session_id}/stream")
async def session_stream(session_id: str) -> StreamingResponse:
    async def event_gen():
        lock = store.lock_for(session_id)
        async with lock:
            state = store.get(session_id)
            if state is None:
                yield sse_encode("error", {"message": "not_found"})
                return
            scenario = effective_scenario(state)
            if scenario is None:
                yield sse_encode("error", {"message": "scenario_missing"})
                return
            if state.phase != Phase.streaming:
                yield sse_encode("error", {"message": "not_streaming"})
                return
            messages = build_ai_messages(scenario, state)

            chunks: list[str] = []
            async for token in stream_chat_completion(messages):
                chunks.append(token)
                yield sse_encode("token", {"t": token})

            narrative_raw = "".join(chunks)

            completed_turn = state.turn_index
            last_player: dict | None = None
            for m in reversed(state.messages):
                if m.get("role") == "player" and m.get("turn") == completed_turn:
                    last_player = m
                    break
            choice_label = (
                str(last_player["choice"]) if last_player and "choice" in last_player else None
            )
            free_src = (
                str(last_player["free_text"]).strip()
                if last_player and "free_text" in last_player
                else None
            )
            display_narrative, _ = parse_score_change_line(narrative_raw)
            display_narrative = display_narrative.strip()

            patch = advance_after_stream(state, scenario, narrative_raw)

            if not patch.get("ended") and state.answer_mode == "ai_options" and state.scenario_mode == "dynamic":
                await ensure_choices_for_turn(state, state.turn_index)
                scenario_next = effective_scenario(state)
                nt = scenario_next.turns[state.turn_index]
                patch["choices"] = list(nt.choices)
                patch["static_line"] = nt.static_line
                if state.turn_generation_error:
                    patch["choices_error"] = state.turn_generation_error

            if is_image_generation_configured() and not patch.get("ended"):
                scenario_for_art = effective_scenario(state)
                scene = build_post_choice_scene_prompt(
                    scenario_title=scenario_for_art.title,
                    completed_turn_index=completed_turn,
                    total_turns=len(scenario_for_art.turns),
                    choice_label=choice_label,
                    free_text_excerpt=free_src,
                    narrative_display=display_narrative,
                )
                patch.update(scenario_art_begin_turn(state))
                asyncio.create_task(_run_question_art_job(session_id, state.turn_index, scene))

            yield sse_encode("state_patch", patch)
            yield sse_encode("done", {})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
