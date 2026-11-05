from scripts.benchmark_models import seconds_from_ns, tokens_per_second


def test_seconds_from_nanoseconds():
    assert seconds_from_ns(1_500_000_000) == 1.5
    assert seconds_from_ns(None) is None
    assert seconds_from_ns(-1) is None


def test_tokens_per_second_uses_ollama_nanosecond_duration():
    assert tokens_per_second(120, 2_000_000_000) == 60.0
    assert tokens_per_second(0, 2_000_000_000) == 0.0
    assert tokens_per_second(120, 0) is None
    assert tokens_per_second(None, 2_000_000_000) is None
