import pytest

from app.config import Settings
from app.llm.factory import (
    active_provider_max_tokens,
    active_provider_model,
    active_provider_name,
    auxiliary_provider_max_tokens,
    auxiliary_provider_model,
    auxiliary_provider_settings,
    build_llm_provider,
)
from app.llm.minimax_client import MiniMaxProvider
from app.llm.provider import LLMConfigurationError
from app.llm.qwen_client import QwenProvider


def test_build_llm_provider_defaults_to_minimax() -> None:
    settings = Settings(minimax_api_key="test-key")

    provider = build_llm_provider(settings)

    assert isinstance(provider, MiniMaxProvider)
    assert active_provider_name(settings) == "minimax"
    assert active_provider_model(settings) == "MiniMax-M3"
    assert active_provider_max_tokens(settings) == 131072


def test_build_llm_provider_selects_qwen() -> None:
    settings = Settings(
        llm_provider="qwen",
        qwen_api_key="test-key",
        qwen_model="qwen3.7-max",
        qwen_max_tokens=8192,
    )

    provider = build_llm_provider(settings)

    assert isinstance(provider, QwenProvider)
    assert active_provider_name(settings) == "qwen"
    assert active_provider_model(settings) == "qwen3.7-max"
    assert active_provider_max_tokens(settings) == 8192


def test_build_llm_provider_rejects_unknown_provider() -> None:
    settings = Settings(llm_provider="unknown")

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM_PROVIDER"):
        build_llm_provider(settings)


def test_auxiliary_provider_profile_is_always_minimax_m27() -> None:
    source = Settings(
        llm_provider="qwen",
        qwen_api_key="qwen-key",
        minimax_api_key="minimax-key",
        minimax_model="MiniMax-M3",
        minimax_max_tokens=131072,
        auxiliary_minimax_model="MiniMax-M2.7",
        auxiliary_minimax_max_tokens=32768,
    )

    auxiliary = auxiliary_provider_settings(source)

    assert auxiliary.llm_provider == "minimax"
    assert auxiliary.minimax_model == "MiniMax-M2.7"
    assert auxiliary.minimax_max_tokens == 32768
    assert auxiliary_provider_model(source) == "MiniMax-M2.7"
    assert auxiliary_provider_max_tokens(source) == 32768
    assert source.llm_provider == "qwen"
    assert source.minimax_model == "MiniMax-M3"
