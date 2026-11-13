from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from agents.base import BaseAgent, build_model
from api.events import EventHub
from api.schemas import MessageInput, SessionCreateInput
from api.sessions import SessionRepository
from config.model_config import ModelConfig
from memory.manager import MemoryManager
from tools.file_manager import FileManager
from tools.tool_executor import ToolExecutor


APP_VERSION = os.getenv("WLASNEAI_OPENCODE_VERSION", "0.1.0")


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


def _opencode_message_view(row: dict[str, Any]) -> dict[str, Any]:
    created = row["created_at"]
    if row["role"] == "user":
        text = "\n".join(part.get("text", "") for part in row["parts"] if part.get("type") == "text")
        return {"id": row["id"], "type": "user", "time": {"created": created}, "text": text}
    text = "\n".join(part.get("text", "") for part in row["parts"] if part.get("type") == "text")
    return {
        "id": row["id"],
        "type": "assistant",
        "time": {"created": created, "completed": created},
        "agent": "wlasneai",
        "model": {"id": row["model_id"], "providerID": row["provider_id"]},
        "content": [{"type": "text", "text": text}],
        "finish": "stop",
        "cost": 0,
        "tokens": {"input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }


def _opencode_model_info(config: ModelConfig, provider_id: str, model_id: str) -> dict[str, Any]:
    provider_names = {
        "ollama": ("Ollama", "ollama"),
        "openrouter": ("OpenRouter", "openai-compatible"),
        "openai_compatible": ("OpenAI compatible", "openai-compatible"),
    }
    name, package = provider_names[provider_id]
    try:
        context = max(1, int(os.getenv("AI_CONTEXT_WINDOW", "8192")))
    except ValueError:
        context = 8192
    return {
        "id": model_id,
        "modelID": model_id,
        "providerID": provider_id,
        "name": model_id,
        "package": package,
        "capabilities": {"tools": True, "input": ["text"], "output": ["text"]},
        "variants": [],
        "time": {"released": 0},
        "cost": [],
        "status": "active",
        "enabled": True,
        "limit": {"context": context, "output": max(1, context // 4)},
    }


def _event(
    event_type: str,
    data: dict[str, Any],
    directory: Path,
    sequence: int | None = None,
) -> dict[str, Any]:
    item = {
        "id": f"evt_{uuid.uuid4().hex}",
        "created": int(time.time() * 1000),
        "type": event_type,
        "location": {"directory": str(directory)},
        "data": data,
    }
    if sequence is not None:
        item["durable"] = {"aggregateID": data["sessionID"], "seq": sequence, "version": 1}
    return item


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = data_dir or _data_dir()
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    temporary = root / "tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    repository = SessionRepository(root / "opencode-sessions.sqlite3", workspace)
    memory = MemoryManager(root / "memory.sqlite3")
    event_hub = EventHub()

    def bridge_event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        durable = {
            "session.inbox.enqueued", "session.inbox.delivered",
            "session.execution.started", "session.execution.succeeded", "session.execution.failed",
            "session.step.started", "session.step.ended", "session.step.failed",
            "session.text.started", "session.text.ended",
        }
        sequence = event_hub.next_sequence(data["sessionID"]) if event_type in durable else None
        return _event(event_type, data, workspace, sequence)

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
    app.state.event_hub = event_hub
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

    @app.get("/api/config")
    async def opencode_config():
        return {"location": {"directory": str(workspace)}, "data": []}

    @app.get("/api/agent")
    async def opencode_agents():
        return {"location": {"directory": str(workspace)}, "data": [{
            "id": "wlasneai",
            "name": "WlasneAI",
            "request": {"settings": {}, "headers": {}, "body": {}},
            "description": "Główny agent WlasneAI",
            "mode": "primary",
            "hidden": False,
            "permissions": [],
        }]}

    @app.get("/api/command")
    async def opencode_commands():
        return {"location": {"directory": str(workspace)}, "data": []}

    @app.get("/api/provider")
    async def opencode_providers():
        providers = {
            "ollama": ("Ollama", "ollama"),
            "openrouter": ("OpenRouter", "openai-compatible"),
            "openai_compatible": ("OpenAI compatible", "openai-compatible"),
        }
        return {"location": {"directory": str(workspace)}, "data": [
            {"id": provider_id, "name": name, "activation": "auto", "package": package}
            for provider_id, (name, package) in providers.items()
        ]}

    @app.get("/api/model")
    async def opencode_models():
        cfg, provider_id, model_id = _model_settings(None)
        return {
            "location": {"directory": str(workspace)},
            "data": [_opencode_model_info(cfg, provider_id, model_id)],
        }

    @app.get("/api/model/default")
    async def opencode_default_model():
        cfg, provider_id, model_id = _model_settings(None)
        return {
            "location": {"directory": str(workspace)},
            "data": _opencode_model_info(cfg, provider_id, model_id),
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

    @app.get("/api/session/active")
    async def opencode_active_sessions():
        return {"data": {}}

    @app.get("/api/event")
    async def opencode_events(request: Request, types: list[str] | None = Query(default=None)):
        async def stream():
            queue = event_hub.subscribe()
            try:
                connected = _event("server.connected", {}, workspace)
                yield f"data: {json.dumps(connected, ensure_ascii=False)}\n\n"
                while not await request.is_disconnected():
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
                        continue
                    if types and item["type"] not in types and item["type"] != "server.connected":
                        continue
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            finally:
                event_hub.unsubscribe(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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

    @app.get("/api/session/{session_id}/message")
    async def opencode_list_messages(session_id: str, limit: int | None = Query(default=None, ge=1, le=200)):
        if not repository.get(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        messages = [_opencode_message_view(item) for item in repository.messages(session_id)]
        if limit is not None:
            messages = messages[-limit:]
        return {"data": messages, "cursor": {}}

    async def execute_opencode_prompt(session_id: str, message_id: str, text: str, cfg: ModelConfig, provider_id: str, model_id: str):
        user = repository.get(session_id)
        if not user:
            return
        await event_hub.publish(bridge_event("session.inbox.delivered", {"sessionID": session_id, "inboxID": message_id}))
        await event_hub.publish(bridge_event("session.execution.started", {"sessionID": session_id}))
        assistant_id = f"msg_{uuid.uuid4().hex}"
        model_ref = {"id": model_id, "providerID": provider_id}
        started = int(time.time() * 1000)
        await event_hub.publish(bridge_event("session.step.started", {
            "sessionID": session_id, "assistantMessageID": assistant_id,
            "agent": "wlasneai", "model": model_ref, "started": started,
        }))
        history = []
        for item in repository.messages(session_id):
            if item["id"] == message_id:
                continue
            if item["role"] in {"user", "assistant"}:
                previous = "\n".join(part.get("text", "") for part in item["parts"] if part.get("type") == "text")
                if previous:
                    history.append({"role": item["role"], "content": previous})
        files = FileManager(workspace)
        tools = ToolExecutor(file_manager=files)
        agent = BaseAgent(model=build_model(cfg), tools=tools, history=history)
        try:
            answer = await run_in_threadpool(agent.run, text)
            answer = answer or "(Model zwrócił pustą odpowiedź.)"
        except Exception as exc:
            error = {"type": "unknown", "message": str(exc)}
            await event_hub.publish(bridge_event("session.step.failed", {
                "sessionID": session_id, "assistantMessageID": assistant_id, "error": error,
            }))
            await event_hub.publish(bridge_event("session.execution.failed", {"sessionID": session_id, "error": error}))
            return
        repository.add_message(
            session_id, "assistant", [{"type": "text", "text": answer}], model_id, provider_id, message_id=assistant_id
        )
        await event_hub.publish(bridge_event("session.text.started", {
            "sessionID": session_id, "assistantMessageID": assistant_id, "ordinal": 0,
        }))
        await event_hub.publish(bridge_event("session.text.delta", {
            "sessionID": session_id, "assistantMessageID": assistant_id, "ordinal": 0, "delta": answer,
        }))
        await event_hub.publish(bridge_event("session.text.ended", {
            "sessionID": session_id, "assistantMessageID": assistant_id, "ordinal": 0, "text": answer,
        }))
        zero_tokens = {"input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}}
        await event_hub.publish(bridge_event("session.step.ended", {
            "sessionID": session_id, "assistantMessageID": assistant_id,
            "finish": "stop", "cost": 0, "tokens": zero_tokens,
        }))
        await event_hub.publish(bridge_event("session.execution.succeeded", {"sessionID": session_id}))

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

    @app.post("/api/session/{session_id}/prompt")
    async def opencode_prompt(session_id: str, payload: dict[str, Any], background_tasks: BackgroundTasks):
        row = repository.get(session_id)
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        prompt = str(payload.get("text", "")).strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        if payload.get("files"):
            raise HTTPException(status_code=501, detail="File attachments are not supported by this bridge yet")
        message_id = payload.get("id")
        if message_id is not None and (not isinstance(message_id, str) or not message_id.startswith("msg_")):
            raise HTTPException(status_code=400, detail="Prompt id must use the OpenCode msg_ format")
        message_id = message_id or f"msg_{uuid.uuid4().hex}"
        delivery = payload.get("delivery", "queue")
        if delivery not in {"steer", "queue"}:
            raise HTTPException(status_code=400, detail="Unsupported prompt delivery mode")
        cfg, provider_id, model_id = _model_settings(None)
        user_message = repository.add_message(
            session_id, "user", [{"type": "text", "text": prompt}], model_id, provider_id, message_id=message_id
        )
        message_payload = {"text": prompt}
        for field in ("agents", "skills", "metadata"):
            if payload.get(field) is not None:
                message_payload[field] = payload[field]
        inbox_item = {"type": "user", "payload": message_payload, "delivery": delivery}
        await event_hub.publish(bridge_event("session.inbox.enqueued", {
            "sessionID": session_id, "inboxID": message_id, "item": inbox_item,
        }))
        background_tasks.add_task(execute_opencode_prompt, session_id, message_id, prompt, cfg, provider_id, model_id)
        return {"data": {
            "id": message_id, "sessionID": session_id,
            "time": {"created": user_message["created_at"]},
            "type": "user", "payload": message_payload, "delivery": delivery,
        }}

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
