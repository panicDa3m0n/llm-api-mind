from app.config import Settings
from app.llm.minimax_client import MiniMaxProvider
from app.llm.provider import LLMConfigurationError, LLMProvider
from app.llm.qwen_client import QwenProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider = _normalized_provider(settings)
    if provider == "minimax":
        return MiniMaxProvider(settings)
    if provider == "qwen":
        return QwenProvider(settings)
    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
        "Supported providers: minimax, qwen."
    )


def active_provider_model(settings: Settings) -> str:
    provider = _normalized_provider(settings)
    if provider == "minimax":
        return settings.minimax_model
    if provider == "qwen":
        return settings.qwen_model
    return settings.llm_provider


def active_provider_name(settings: Settings) -> str:
    return _normalized_provider(settings)


def active_provider_max_tokens(settings: Settings) -> int:
    provider = _normalized_provider(settings)
    if provider == "minimax":
        return settings.minimax_max_tokens
    if provider == "qwen":
        return settings.qwen_max_tokens
    return settings.minimax_max_tokens


def _normalized_provider(settings: Settings) -> str:
    return settings.llm_provider.strip().lower()
