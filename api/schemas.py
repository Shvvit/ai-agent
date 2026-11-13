from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MessagePart(BaseModel):
    type: str = "text"
    text: str = ""


class MessageInput(BaseModel):
    parts: list[MessagePart] = Field(default_factory=list)
    model: dict[str, str] | None = None
    agent: str | None = None
    system: str | None = None
    variant: str | None = None


class SessionCreateInput(BaseModel):
    title: str | None = None
    parentID: str | None = None


class Session(BaseModel):
    id: str
    projectID: str = "wlasneai"
    directory: str
    title: str
    version: str = "1.0.0"
    time: dict[str, int]


class MessageInfo(BaseModel):
    id: str
    sessionID: str
    role: str
    time: dict[str, int]
    modelID: str
    providerID: str
    mode: str = "chat"
    agent: str = "wlasneai"
    finish: str = "stop"
    cost: float = 0.0
    tokens: dict[str, int] = Field(default_factory=lambda: {"input": 0, "output": 0})


class MessageOutput(BaseModel):
    info: MessageInfo
    parts: list[dict[str, Any]]
