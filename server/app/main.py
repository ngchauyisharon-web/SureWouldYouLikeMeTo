from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.ai_provider import stream_chat_completion
from app.config import settings
from app.game_engine import (
    Phase,
    advance_after_stream,
    apply_answer_mode,
    apply_choice,
    apply_free_text,
    build_ai_messages,
    initial_client_snapshot,
    parse_score_change_line,
    sse_encode,
    store,
)
from app.image_gen import (
    build_outcome_scene_prompt,
    build_scenario_scene_prompt,
    generate_outcome_image_b64,
    is_image_generation_configured,
)
from app.neurobot_coach import neurobot_coach_turn
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


class ChoiceBody(BaseModel):
    choice_index: int = Field(..., ge=0)


class AnswerModeBody(BaseModel):
    mode: str = Field(..., pattern="^(free_text|ai_options)$")


class FreeTextBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NeuroBotBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)


async def _run_outcome_image_job(session_id: str, scene_prompt: str) -> None:
    lock = store.lock_for(session_id)
    async with lock:
        st = store.get(session_id)
        if st is None:
            return
        st.outcome_image_status = "pending"
        st.outcome_image_b64 = None
    b64: str | None = None
    try:
        b64 = await generate_outcome_image_b64(scene_prompt)
    except Exception as e:
        logging.getLogger(__name__).warning("outcome_image_job_error: %s", e)
        b64 = None
    async with lock:
        st = store.get(session_id)
        if st is None:
            return
        if b64:
            st.outcome_image_b64 = b64
            st.outcome_image_status = "ready"
        else:
            st.outcome_image_status = "failed"


async def _run_scenario_art_job(session_id: str, scene_prompt: str) -> None:
    lock = store.lock_for(session_id)
    async with lock:
        st = store.get(session_id)
        if st is None:
            return
        st.scenario_art_status = "pending"
        st.scenario_art_b64 = None
    b64: str | None = None
    try:
        b64 = await generate_outcome_image_b64(scene_prompt)
    except Exception as e:
        logging.getLogger(__name__).warning("scenario_art_job_error: %s", e)
        b64 = None
    async with lock:
        st = store.get(session_id)
        if st is None:
            return
        if b64:
            st.scenario_art_b64 = b64
            st.scenario_art_status = "ready"
        else:
            st.scenario_art_status = "failed"
            logging.getLogger(__name__).warning(
                "scenario_art_job_no_image session_id_prefix=%s",
                session_id[:13],
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
    scenario = get_scenario(body.scenario_slug)
    assert scenario is not None
    if is_image_generation_configured():
        turn0 = scenario.turns[0]
        scene = build_scenario_scene_prompt(
            scenario_title=scenario.title,
            tagline=scenario.tagline,
            body=scenario.body,
            turn0_static_line=turn0.static_line,
        )
        state.scenario_art_status = "pending"
        asyncio.create_task(_run_scenario_art_job(state.session_id, scene))
    snap = initial_client_snapshot(state, scenario)
    return snap


@app.post("/api/sessions/{session_id}/answer-mode")
async def post_answer_mode(session_id: str, body: AnswerModeBody) -> dict:
    lock = store.lock_for(session_id)
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found") from None
        scenario = get_scenario(state.scenario_slug)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario_missing") from None
        try:
            return apply_answer_mode(state, scenario, body.mode)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None


@app.post("/api/sessions/{session_id}/free-text")
async def post_free_text(session_id: str, body: FreeTextBody) -> dict:
    lock = store.lock_for(session_id)
    async with lock:
        state = store.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="not_found") from None
        if state.phase != Phase.awaiting_choice:
            raise HTTPException(status_code=400, detail="not_awaiting_choice") from None
        scenario = get_scenario(state.scenario_slug)
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
        scenario = get_scenario(state.scenario_slug)
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
        scenario = get_scenario(state.scenario_slug)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario_missing") from None
        reply = await neurobot_coach_turn(state, scenario, body.message)
        return {"reply": reply, "neural_score": state.neural_score}


@app.get("/api/sessions/{session_id}/outcome-image")
def get_outcome_image(session_id: str) -> dict:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {"status": state.outcome_image_status, "b64": state.outcome_image_b64}


@app.get("/api/sessions/{session_id}/scenario-art")
def get_scenario_art(session_id: str) -> dict:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {"status": state.scenario_art_status, "b64": state.scenario_art_b64}


@app.get("/api/sessions/{session_id}/stream")
async def session_stream(session_id: str) -> StreamingResponse:
    async def event_gen():
        lock = store.lock_for(session_id)
        async with lock:
            state = store.get(session_id)
            if state is None:
                yield sse_encode("error", {"message": "not_found"})
                return
            scenario = get_scenario(state.scenario_slug)
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
            turn_idx = state.turn_index
            last_player: dict | None = None
            for m in reversed(state.messages):
                if m.get("role") == "player" and m.get("turn") == turn_idx:
                    last_player = m
                    break
            choice_label = str(last_player["choice"]) if last_player and "choice" in last_player else None
            display_narrative = narrative_raw.strip()
            if last_player is not None and "free_text" in last_player:
                display_narrative, _ = parse_score_change_line(narrative_raw)

            patch = advance_after_stream(state, scenario, narrative_raw)

            if is_image_generation_configured():
                scene = build_outcome_scene_prompt(
                    scenario_title=scenario.title,
                    narrative_display=display_narrative,
                    choice_label=choice_label,
                )
                asyncio.create_task(_run_outcome_image_job(session_id, scene))

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
