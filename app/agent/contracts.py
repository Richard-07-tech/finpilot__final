from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None


class ChatTurn(BaseModel):
    role: str
    content: str


class SessionContext(BaseModel):
    session_id: str
    user_id: str
    turns: list[ChatTurn] = Field(default_factory=list)
    budget_goals: dict | None = None
