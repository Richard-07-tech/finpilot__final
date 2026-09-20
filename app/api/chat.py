"""Chat endpoint for the FinPilot tool-calling assistant."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import context_store
from app.agent.orchestrator import run_turn


router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    answer: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or context_store.create_session(request.user_id)
    session = context_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="session does not belong to this user")
    try:
        answer = run_turn(session_id, request.message)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="session not found") from error
    return ChatResponse(session_id=session_id, answer=answer)
