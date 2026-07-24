from app.config import Settings
from app.llm.minimax_client import AnthropicCompatibleProvider


class QwenProvider(AnthropicCompatibleProvider):
    """Qwen provider through Alibaba Model Studio's Anthropic-compatible API."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            api_key=settings.qwen_api_key,
            api_key_name="QWEN_API_KEY",
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
            max_tokens=settings.qwen_max_tokens,
            provider_name="Qwen",
            stream_max_attempts=settings.provider_stream_max_attempts,
            stream_retry_backoff_seconds=(
                settings.provider_stream_retry_backoff_seconds
            ),
            max_token_continuations=settings.provider_max_token_continuations,
        )
