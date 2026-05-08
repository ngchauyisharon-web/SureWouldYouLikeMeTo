from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.game_engine import (
    Phase,
    advance_after_stream,
    apply_choice,
    build_ai_messages,
    initial_client_snapshot,
    sse_encode,
    store,
)
from app.scenarios import get_scenario, list_scenario_summaries
from app.ai_provider import stream_chat_completion

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
    return initial_client_snapshot(state, scenario)


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
        except ValueError:
            raise HTTPException(status_code=400, detail="bad_choice") from None
        state.phase = Phase.streaming
    return {"ok": True}


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

            narrative = "".join(chunks)
            patch = advance_after_stream(state, scenario, narrative)
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
