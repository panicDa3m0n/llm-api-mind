from dataclasses import dataclass
from pathlib import Path

from app.config import Settings


DEFAULT_AGENT_SYSTEM_PROMPT_PATH = Path(__file__).with_name("scarlet_system.md")


class AgentSystemPromptError(RuntimeError):
    """Raised when the configured agent system prompt cannot be loaded."""


@dataclass(frozen=True)
class AgentSystemPrompt:
    content: str
    source: str
    path: str | None = None


def resolve_agent_system_prompt(
    settings: Settings,
    *,
    override: str | None = None,
) -> AgentSystemPrompt:
    """Resolve the effective agent system prompt for a chat turn."""

    if override and override.strip():
        return AgentSystemPrompt(content=override.strip(), source="request")

    if settings.agent_system_prompt and settings.agent_system_prompt.strip():
        return AgentSystemPrompt(
            content=settings.agent_system_prompt.strip(),
            source="environment",
        )

    prompt_path = _prompt_path(settings)
    try:
        content = prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise AgentSystemPromptError(
            f"Agent system prompt could not be loaded from {prompt_path}."
        ) from exc

    if not content:
        raise AgentSystemPromptError(
            f"Agent system prompt is empty at {prompt_path}."
        )

    return AgentSystemPrompt(
        content=content,
        source="configured_path" if settings.agent_system_prompt_path else "bundled",
        path=str(prompt_path),
    )


def _prompt_path(settings: Settings) -> Path:
    if not settings.agent_system_prompt_path:
        return DEFAULT_AGENT_SYSTEM_PROMPT_PATH

    path = Path(settings.agent_system_prompt_path).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path
