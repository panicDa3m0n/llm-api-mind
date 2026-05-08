from typing import Any

import anthropic

from app.config import Settings
from app.llm.provider import LLMConfigurationError, LLMRequestError, LLMTextResult


class MiniMaxProvider:
    """MiniMax M2 provider through the Anthropic-compatible API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.minimax_api_key:
            raise LLMConfigurationError("MINIMAX_API_KEY is not configured.")

        self._settings = settings
        self._client = anthropic.Anthropic(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        )

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        effective_max_tokens = max_tokens or self._settings.minimax_max_tokens
        try:
            message = self._client.messages.create(
                model=self._settings.minimax_model,
                max_tokens=effective_max_tokens,
                system=system or "You are a concise diagnostic assistant.",
                messages=[
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            )
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        return LLMTextResult(
            model=getattr(message, "model", self._settings.minimax_model),
            text=self._extract_text(message.content),
            usage=self._extract_usage(message),
        )

    def _sanitize_error(self, message: str) -> str:
        api_key = self._settings.minimax_api_key
        if api_key:
            return message.replace(api_key, "***")
        return message

    @staticmethod
    def _extract_text(content_blocks: list[Any]) -> str:
        text_parts: list[str] = []
        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "")
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts).strip()

    @staticmethod
    def _extract_usage(message: Any) -> dict[str, Any]:
        usage = getattr(message, "usage", None)
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if isinstance(usage, dict):
            return usage
        return {}
