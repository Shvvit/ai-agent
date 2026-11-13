from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from agents.base import BaseAgent, build_model
from api.schemas import MessageInput, SessionCreateInput
from api.sessions import SessionRepository
from config.model_config import ModelConfig
from memory.manager import MemoryManager
from tools.file_manager import FileManager
from tools.tool_executor import ToolExecutor


APP_VERSION = "0.1.0"


def _data_dir() -> Path:
    root = Path(os.getenv("APPDATA", Path.home() / "AppData/Roaming")) / "WlasneAI"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _model_settings(payload: dict[str, str] | None) -> tuple[ModelConfig, str, str]:
    if not payload:
        cfg = ModelConfig.from_env()
        return cfg, cfg.provider, cfg.model
    provider = payload.get("providerID", os.getenv("AI_PROVIDER", "ollama")).strip().lower()
    model = payload.get("modelID", os.getenv("AI_MODEL", "qwen3:8b")).strip()
    allowed = {"ollama", "openrouter", "openai_compatible"}
    if provider not in allowed or not model:
        raise HTTPException(status_code=400, detail="Nieobsługiwany dostawca lub pusty model.")
    defaults = {
        "ollama": "http://127.0.0.1:11434",
        "openrouter": "https://openrouter.ai/api/v1",
        "openai_compatible": "https://api.openai.com/v1",
    }
    host = os.getenv("AI_HOST", os.getenv("AI_BASE_URL", defaults[provider]))
    api_key = os.getenv("AI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    cfg = ModelConfig(
        provider=provider, model=model, host=host,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.2")),
        api_key=api_key,
        timeout=float(os.getenv("AI_TIMEOUT", "120")),
    )
    return cfg, provider, model


def _session_view(row: dict[str, Any], directory: Path) -> dict[str, Any]:
    return {
        "id": row["id"], "projectID": "wlasneai",
        "directory": str(directory), "title": row["title"],
        "version": APP_VERSION,
        "time": {"created": row["created_at"], "updated": row["updated_at"]},
    }


def _opencode_session_view(row: dict[str, Any], directory: Path) -> dict[str, Any]:
    return {
        "id": row["id"],
        "projectID": "wlasneai",
        "cost": 0,
        "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}},
        "time": {"created": row["created_at"], "updated": row["updated_at"]},
        "title": row["title"],
        "location": {"directory": str(directory)},
    }


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = data_dir or _data_dir()
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    temporary = root / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    repository = SessionRepository(root / "opencode-sessions.sqlite3", workspace)
    memory = MemoryManager(root / "memory.sqlite3")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.sessions = repository
        app.state.memory = memory
        yield
        repository.close()
        memory.close()

    app = FastAPI(title="WlasneAI OpenCode Bridge", version=APP_VERSION, lifespan=lifespan)
    app.state.sessions = repository
    app.state.memory = memory
    app.state.workspace = workspace
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "app://."],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/global/health")
    async def health():
        return {"healthy": True, "version": APP_VERSION, "backend": "wlasneai"}

    @app.get("/api/info")
    async def server_info(request: Request):
        """Implement the pinned OpenCode server.info readiness contract."""
        return {
            "version": APP_VERSION,
            "pid": os.getpid(),
            "urls": [str(request.base_url).rstrip("/")],
            "paths": {"tmp": str(temporary)},
        }

    @app.get("/project")
    async def projects():
        return [{
            "id": "wlasneai", "worktree": str(workspace),
            "vcs": "git", "time": {"created": 0, "updated": 0},
            "sandboxes": [], "name": "WlasneAI",
        }]

    @app.get("/api/project")
    async def opencode_projects():
        now = int(time.time())
        return [{
            "id": "wlasneai",
            "canonical": str(workspace),
            "name": "WlasneAI",
            "time": {"created": now, "updated": now, "active": now},
            "sandboxes": [],
        }]

    @app.get("/api/location")
    async def opencode_location():
        directory = str(workspace)
        return {
            "directory": directory,
            "project": {
                "id": "wlasneai",
                "directory": directory,
                "canonical": directory,
            },
        }

    @app.get("/path")
    async def path_info():
        return {"home": str(root), "state": str(root), "config": str(root)}

    @app.get("/session")
    async def list_sessions(directory: str | None = Query(default=None)):
        return [_session_view(row, workspace) for row in repository.list()]

    @app.get("/api/session")
    async def opencode_list_sessions(
        limit: int | None = Query(default=None, ge=1, le=200),
        directory: str | None = Query(default=None),
        project: str | None = Query(default=None),
    ):
        rows = repository.list()
        if limit is not None:
            rows = rows[:limit]
        return {"data": [_opencode_session_view(row, workspace) for row in rows], "cursor": {}}

    @app.post("/session")
    async def create_session(payload: SessionCreateInput):
        row = repository.create(payload.title or "New session")
        return _session_view(row, workspace)

    @app.post("/api/session")
    async def opencode_create_session(payload: SessionCreateInput):
        row = repository.create(payload.title or "New session")
        return {"data": _opencode_session_view(row, workspace)}

    @app.get("/session/{session_id}")
    async def get_session(session_id: str):
        row = repository.get(session_id)
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        return _session_view(row, workspace)

    @app.get("/api/session/{session_id}")
    async def opencode_get_session(session_id: str):
        row = repository.get(session_id)
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"data": _opencode_session_view(row, workspace)}

    @app.delete("/session/{session_id}")
    async def delete_session(session_id: str):
        if not repository.delete(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return True

    @app.delete("/api/session/{session_id}", status_code=204)
    async def opencode_delete_session(session_id: str):
        if not repository.delete(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return Response(status_code=204)

    @app.patch("/session/{session_id}")
    async def update_session(session_id: str, payload: dict[str, Any]):
        if not repository.get(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        title = payload.get("title")
        if isinstance(title, str) and title.strip():
            repository.update_title(session_id, title.strip())
        return _session_view(repository.get(session_id), workspace)

    @app.get("/session/{session_id}/message")
    async def list_messages(session_id: str):
        if not repository.get(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        result = []
        for item in repository.messages(session_id):
            info = {
                "id": item["id"], "sessionID": session_id, "role": item["role"],
                "time": {"created": item["created_at"]},
                "modelID": item["model_id"], "providerID": item["provider_id"],
                "mode": "chat", "agent": "wlasneai", "finish": "stop",
                "cost": 0, "tokens": {"input": 0, "output": 0},
            }
            result.append({"info": info, "parts": item["parts"]})
        return result

    @app.post("/session/{session_id}/message")
    async def send_message(session_id: str, payload: MessageInput):
        if not repository.get(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        prompt = "\n".join(part.text for part in payload.parts if part.type == "text").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Wiadomość nie może być pusta.")
        cfg, provider_id, model_id = _model_settings(payload.model)
        repository.add_message(
            session_id, "user", [{"type": "text", "text": prompt}], model_id, provider_id
        )
        history = []
        for item in repository.messages(session_id)[:-1]:
            if item["role"] in {"user", "assistant"}:
                text_content = "\n".join(
                    part.get("text", "") for part in item["parts"] if part.get("type") == "text"
                )
                if text_content:
                    history.append({"role": item["role"], "content": text_content})
        files = FileManager(workspace)
        tools = ToolExecutor(file_manager=files)
        agent = BaseAgent(model=build_model(cfg), tools=tools, history=history)
        answer = await run_in_threadpool(agent.run, prompt)
        answer = answer or "(Model zwrócił pustą odpowiedź.)"
        assistant_message = repository.add_message(
            session_id, "assistant", [{"type": "text", "text": answer}], model_id, provider_id
        )
        return {
            "info": {
                "id": assistant_message["id"], "sessionID": session_id, "role": "assistant",
                "time": {"created": assistant_message["created_at"], "completed": assistant_message["created_at"]},
                "modelID": model_id, "providerID": provider_id, "mode": "chat",
                "agent": payload.agent or "wlasneai", "finish": "stop",
                "cost": 0, "tokens": {"input": 0, "output": 0},
            },
            "parts": assistant_message["parts"],
        }

    @app.get("/event")
    async def events():
        async def stream():
            yield 'data: {"type":"server.connected","properties":{}}\n\n'
        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/provider")
    async def providers():
        return {"all": [
            {"id": "ollama", "name": "Ollama", "models": {}},
            {"id": "openrouter", "name": "OpenRouter", "models": {}},
            {"id": "openai_compatible", "name": "OpenAI compatible", "models": {}},
        ], "default": {"ollama": os.getenv("AI_MODEL", "qwen3:8b")}}

    @app.get("/agent")
    async def agents():
        return [{"name": "wlasneai", "description": "Główny agent WlasneAI", "mode": "primary"}]

    @app.get("/command")
    async def commands():
        return []

    return app


app = create_app()
