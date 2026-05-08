from typing import Any

import anthropic

from app.config import Settings
from app.llm.provider import (
    LLMConfigurationError,
    LLMMessage,
    LLMRequestError,
    LLMTextResult,
)


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
        return self.generate_chat(
            messages=[LLMMessage(role="user", content=prompt)],
            system=system,
            max_tokens=max_tokens,
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        effective_max_tokens = max_tokens or self._settings.minimax_max_tokens
        try:
            message = self._client.messages.create(
                model=self._settings.minimax_model,
                max_tokens=effective_max_tokens,
                system=system or "You are a concise assistant.",
                messages=[self._to_anthropic_message(item) for item in messages],
            )
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        return LLMTextResult(
            model=getattr(message, "model", self._settings.minimax_model),
            text=self._extract_text(message.content),
            usage=self._extract_usage(message),
            provider_message_id=getattr(message, "id", None),
            raw_content=self._extract_raw_content(message.content),
            stop_reason=getattr(message, "stop_reason", None),
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
    def _to_anthropic_message(message: LLMMessage) -> dict[str, Any]:
        return {
            "role": message.role,
            "content": [{"type": "text", "text": message.content}],
        }

    @staticmethod
    def _extract_raw_content(content_blocks: list[Any]) -> list[dict[str, Any]]:
        raw_blocks: list[dict[str, Any]] = []
        for block in content_blocks:
            if hasattr(block, "model_dump"):
                raw_blocks.append(block.model_dump())
            elif isinstance(block, dict):
                raw_blocks.append(block)
        return raw_blocks

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
