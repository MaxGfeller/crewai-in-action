"""FastAPI AG-UI adapter for the CrewAI conversation Flow."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from ag_ui.core import (
    CustomEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder

from account_assistant.conversation import get_conversation_service
from account_assistant.services.account_http import get_account_service
from account_assistant.settings import require_openai_api_key
from account_assistant.state import PendingAction


@asynccontextmanager
async def lifespan(_app: FastAPI):
    require_openai_api_key()
    yield


app = FastAPI(
    title="account-assistant-agui",
    version="0.1.0",
    description="Local AG-UI adapter around the Chapter 7 CrewAI conversation Flow.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4207",
        "http://127.0.0.1:4207",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _last_user_message(input_data: RunAgentInput) -> str:
    for message in reversed(input_data.messages or []):
        if getattr(message, "role", None) == "user":
            content = getattr(message, "content", "")
            return content if isinstance(content, str) else str(content or "")
    return ""


def _input_state(input_data: RunAgentInput) -> dict[str, Any]:
    state = getattr(input_data, "state", None)
    return state if isinstance(state, dict) else {}


def _chunk_text(text: str, size: int = 80) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)] or [""]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/threads")
def list_threads(limit: int = 50) -> dict:
    threads = get_conversation_service().list_threads(limit=limit)
    return {"threads": [thread.model_dump() for thread in threads], "nextCursor": None}


@app.post("/threads")
async def create_thread() -> dict:
    thread = get_conversation_service().create_thread()
    return thread.model_dump()


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str) -> JSONResponse:
    thread = get_conversation_service().get_thread(thread_id)
    if thread is None:
        return JSONResponse({"error": "thread not found"}, status_code=404)
    return JSONResponse(thread.model_dump())


@app.get("/accounts")
def list_accounts() -> dict:
    accounts = get_account_service().list_accounts()
    return {"accounts": [account.model_dump() for account in accounts]}


@app.post("/agui")
async def agui(input_data: RunAgentInput, request: Request):
    encoder = EventEncoder(accept=request.headers.get("accept"))

    async def event_generator():
        try:
            yield encoder.encode(
                RunStartedEvent(
                    type=EventType.RUN_STARTED,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                )
            )

            message = _last_user_message(input_data)
            state = _input_state(input_data)
            result = get_conversation_service().run_turn(
                message=message,
                thread_id=input_data.thread_id,
                active_account_id=state.get("active_account_id"),
            )
            snapshot = result.state_snapshot()

            for trace in result.state.tool_traces:
                tool_call_id = trace.trace_id
                yield encoder.encode(
                    ToolCallStartEvent(
                        type=EventType.TOOL_CALL_START,
                        tool_call_id=tool_call_id,
                        tool_call_name=trace.name,
                    )
                )
                yield encoder.encode(
                    ToolCallArgsEvent(
                        type=EventType.TOOL_CALL_ARGS,
                        tool_call_id=tool_call_id,
                        delta=json.dumps(trace.args),
                    )
                )
                yield encoder.encode(
                    ToolCallEndEvent(
                        type=EventType.TOOL_CALL_END,
                        tool_call_id=tool_call_id,
                    )
                )
                yield encoder.encode(
                    ToolCallResultEvent(
                        type=EventType.TOOL_CALL_RESULT,
                        message_id=f"tool_result_{tool_call_id}",
                        tool_call_id=tool_call_id,
                        content=trace.result_preview,
                        role="tool",
                    )
                )

            yield encoder.encode(
                StateSnapshotEvent(
                    type=EventType.STATE_SNAPSHOT,
                    snapshot=snapshot,
                )
            )

            for surface in result.state.ui_surfaces:
                yield encoder.encode(
                    CustomEvent(
                        type=EventType.CUSTOM,
                        name="a2ui.surface",
                        value=surface.model_dump(),
                    )
                )

            for action in result.state.pending_actions:
                yield encoder.encode(
                    CustomEvent(
                        type=EventType.CUSTOM,
                        name="account.pending_action",
                        value=action.model_dump(),
                    )
                )

            message_id = f"msg_{uuid.uuid4().hex[:8]}"
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )
            for chunk in _chunk_text(result.reply):
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=chunk,
                    )
                )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id,
                )
            )
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                )
            )
        except Exception as exc:
            yield encoder.encode(
                RunErrorEvent(type=EventType.RUN_ERROR, message=str(exc))
            )

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
    )


@app.post("/actions/approve")
async def approve_action(body: dict) -> JSONResponse:
    action = PendingAction.model_validate(body.get("action", body))
    result = get_conversation_service().approve_action(action)
    return JSONResponse({"ok": True, "result": result})


def serve() -> None:
    import uvicorn

    require_openai_api_key()
    host = os.getenv("ACCOUNT_ASSISTANT_HOST", "127.0.0.1")
    port = int(os.getenv("ACCOUNT_ASSISTANT_PORT", "8097"))
    uvicorn.run("account_assistant.server:app", host=host, port=port, reload=False)
