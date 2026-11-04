from models.registry import ModelRegistry
from models.router import ModelRouter


def test_registry_normalizes_and_sorts_ollama_models():
    registry = ModelRegistry.from_ollama_payload({"models": [
        {"name": "large:latest", "size": 900},
        {"name": "small:latest", "size": 100},
        {"size": 50},
    ]})
    assert [model.name for model in registry.list()] == ["small:latest", "large:latest"]


def test_router_selects_configured_task_profile():
    registry = ModelRegistry.from_ollama_payload({"models": [
        {"name": "qwen3:8b", "size": 8},
        {"name": "qwen2.5-coder:7b", "size": 7},
    ]})
    router = ModelRouter(registry, "qwen3:8b", {"coding": "qwen2.5-coder:7b"})
    choice = router.choose("Napisz program w Pythonie")
    assert choice.model == "qwen2.5-coder:7b"
    assert choice.profile == "coding"


def test_router_falls_back_when_profile_model_is_missing():
    registry = ModelRegistry.from_ollama_payload({"models": [
        {"name": "qwen3:8b", "size": 8},
    ]})
    router = ModelRouter(registry, "qwen3:8b", {"coding": "missing:model"})
    assert router.choose("debug program").model == "qwen3:8b"


def test_router_uses_smallest_available_when_default_is_missing():
    registry = ModelRegistry.from_ollama_payload({"models": [
        {"name": "large", "size": 90},
        {"name": "small", "size": 10},
    ]})
    choice = ModelRouter(registry, "missing", {}).choose("Hello")
    assert choice.model == "small"



def test_registry_rejects_non_object_payload():
    import pytest

    with pytest.raises(ValueError):
        ModelRegistry.from_ollama_payload([])
