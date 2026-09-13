"""Unit tests for unavailable models filtering and client resilience."""
import os
import json
from unittest.mock import patch
from src.models.client import (
    UnifiedModelClient,
    load_unavailable_models,
    persist_unavailable_model,
    should_mark_model_unavailable,
    _normalize_model_ref,
)


def test_normalize_model_ref():
    assert _normalize_model_ref("gemini-2.5-flash", "nvidia_nim") == ("gemini", "gemini-2.5-flash")
    assert _normalize_model_ref("nvidia/nemotron-3.5-lightning-30b-a3b", "gemini") == ("nvidia_nim", "nvidia/nemotron-3.5-lightning-30b-a3b")
    assert _normalize_model_ref({"provider": "nvidia_nim", "model": "openai/gpt-oss-20b"}, "gemini") == ("nvidia_nim", "openai/gpt-oss-20b")


def test_should_mark_model_unavailable():
    assert should_mark_model_unavailable("nvidia_nim", Exception("Error 404: model not found")) is True
    assert should_mark_model_unavailable("nvidia_nim", Exception("503 Service Unavailable")) is False
    assert should_mark_model_unavailable("gemini", Exception("400 Invalid argument: model is not supported")) is True


def test_unified_model_client_filters_unavailable_models():
    fake_unavailable = {
        "nvidia_nim": {"google/gemma-4-31b-it", "nvidia/llama-3.1-nemotron-70b-instruct"},
        "gemini": {"gemini-2.5-flash-lite"},
    }

    config = {
        "provider": "nvidia_nim",
        "model": "google/gemma-4-31b-it", # 차단된 모델
        "fallback_models": [
            "nvidia/llama-3.1-nemotron-70b-instruct", # 차단된 모델
            "nvidia/nemotron-3.5-lightning-30b-a3b", # 사용 가능한 모델
            "gemini-2.5-flash", # 사용 가능한 모델
        ],
    }

    with patch("src.models.client.load_unavailable_models", return_value=fake_unavailable):
        client = UnifiedModelClient("test_agent", config)

        # 차단된 2개 모델이 제외되고, 사용 가능한 모델만 후보군에 남아야 함
        assert "google/gemma-4-31b-it" not in client.candidate_models
        assert "nvidia/llama-3.1-nemotron-70b-instruct" not in client.candidate_models
        assert "nvidia/nemotron-3.5-lightning-30b-a3b" in client.candidate_models
        assert "gemini-2.5-flash" in client.candidate_models
        # 첫 번째 가용 모델이 primary로 승격
        assert client.primary_model == "nvidia/nemotron-3.5-lightning-30b-a3b"

