import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlmodel import Session

from app.llm.factory import active_provider_max_tokens
from app.llm.provider import LLMConfigurationError, LLMRequestError
from app.mind.memory import MemoryOperationResult, MindAPIContext
from app.mind.search import (
    search_documents,
    sparse_results_by_source,
    sync_session_documents,
)
from app.mind.time_filters import TimeFilter, interval_contains, resolve_interval, time_filter_payload
from app.storage import repositories
from app.storage.models import ChatSession, MemoryRecord, Message, SessionSummary


SESSION_SUMMARY_VERSION = "episodic-v1"


SESSION_SUMMARY_SYSTEM_PROMPT = """You compact a chat session for Scarlet's episodic memory.

You are not speaking to the user. Return only one JSON object.

The summary is a navigation index for Scarlet, not a replacement for the exact
transcript. Base it on the complete user<->assistant conversation history that
you receive. Preserve important decisions, preferences, corrections,
unresolved questions, and memory provenance cues. Do not invent facts.

Required JSON shape:

{
  "summary": "compact descriptive summary of the conversation substance",
  "topics": ["topic"],
  "decisions": ["decision or accepted direction"],
  "open_questions": ["unresolved question"],
  "notable_context": ["short source-sensitive note"]
}
"""


SESSION_SUMMARY_REPAIR_SYSTEM_PROMPT = """Repair malformed session summary JSON.

Return only one valid JSON object matching the requested shape. Preserve the
meaning when possible. Do not add markdown, prose, or code fences.
"""


class SessionsListBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    query: str | None = Field(default=None, max_length=500)
    time: TimeFilter | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for alias in ("top_k", "count", "page_size", "last", "recent"):
            if "limit" not in normalized and alias in normalized:
                normalized["limit"] = normalized.pop(alias)
        if "q" in normalized and "query" not in normalized:
            normalized["query"] = normalized.pop("q")
        if "time" not in normalized:
            for alias in ("when", "period", "date_range"):
                if alias in normalized:
                    normalized["time"] = normalized.pop(alias)
                    break
        return normalized

    @model_validator(mode="after")
    def validate_time_basis(self) -> "SessionsListBody":
        if self.time is not None:
            basis = self.time.basis or "conversation"
            if basis not in {"conversation", "created", "updated", "summary"}:
                raise ValueError(
                    "time.basis must be conversation, created, updated, or summary"
                )
            self.time.basis = basis
        return self


class SessionReadBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_messages: bool = True
    include_memories: bool = True
    message_limit: int | None = Field(default=None, ge=1, le=2000)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "limit" in normalized and "message_limit" not in normalized:
            normalized["message_limit"] = normalized.pop("limit")
        if "messages" in normalized and "include_messages" not in normalized:
            normalized["include_messages"] = normalized.pop("messages")
        if "memories" in normalized and "include_memories" not in normalized:
            normalized["include_memories"] = normalized.pop("memories")
        return normalized


class SessionSummarizeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    focus: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "refresh" in normalized and "force" not in normalized:
            normalized["force"] = normalized.pop("refresh")
        if "summary_focus" in normalized and "focus" not in normalized:
            normalized["focus"] = normalized.pop("summary_focus")
        return normalized


def handle_sessions_list(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _context_required("sessions.list")
    try:
        request = SessionsListBody.model_validate(body)
    except ValidationError as exc:
        return _validation_error("sessions.list", exc)

    with Session(context.engine) as db:
        query = _normalized_query(request.query)
        resolved_time = resolve_interval(request.time)
        candidates = repositories.list_chat_sessions(db, limit=500, offset=0)
        candidates = _filter_sessions_by_time(
            db,
            candidates,
            time_filter=request.time,
            resolved_time=resolved_time,
            context=context,
        )
        if query is not None:
            sync_session_documents(db, candidates)
            sparse_matches = sparse_results_by_source(
                search_documents(
                    db,
                    query=query,
                    kind="session",
                    limit=max(80, request.limit * 10),
                )
            )
            matched = [
                chat_session
                for chat_session in candidates
                if chat_session.id in sparse_matches
                or _session_matches_query(db, chat_session, query)
            ]
            matched.sort(
                key=lambda chat_session: (
                    sparse_matches.get(chat_session.id).score
                    if chat_session.id in sparse_matches
                    else 0.0,
                    chat_session.updated_at,
                ),
                reverse=True,
            )
        else:
            matched = candidates
        selected_sessions = matched[request.offset : request.offset + request.limit]
        has_more = request.offset + request.limit < len(matched)

        session_payloads = [
            _session_index_payload(
                db,
                chat_session,
                sparse_match=sparse_matches.get(chat_session.id)
                if query is not None
                else None,
            )
            for chat_session in selected_sessions
        ]

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "sessions.list",
            "intent": intent,
            "limit": request.limit,
            "offset": request.offset,
            "query": request.query,
            "time": time_filter_payload(request.time, resolved_time),
            "retrieval_stages": ["fts5_sparse_v1", "fallback_summary_text_match_v1"],
            "count": len(session_payloads),
            "has_more": has_more,
            "sessions": session_payloads,
        },
        cognitive_hint=(
            "Use session summaries as an episodic navigation index. When exact "
            "wording or provenance matters, read the full session by id."
        ),
        suggested_next_actions=[
            "Call GET /mind/sessions/{session_id} for the exact transcript",
            "Call POST /mind/sessions/{session_id}/summarize if a session has only a fallback summary",
        ],
        confidence=0.92,
    )


def handle_session_read(
    session_id: str,
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _context_required("sessions.read")
    try:
        request = SessionReadBody.model_validate(body)
    except ValidationError as exc:
        return _validation_error("sessions.read", exc)

    with Session(context.engine) as db:
        chat_session = repositories.get_chat_session(db, session_id)
        if chat_session is None:
            return _session_not_found(session_id, operation="sessions.read")

        messages = repositories.list_messages(db, session_id=session_id)
        all_message_count = len(messages)
        truncated = False
        if request.message_limit is not None and len(messages) > request.message_limit:
            messages = messages[-request.message_limit :]
            truncated = True

        summary = repositories.get_session_summary(db, session_id=session_id)
        memories = (
            repositories.list_memories_for_session(db, session_id=session_id)
            if request.include_memories
            else []
        )
        summary_payload = _summary_or_fallback_payload(
            chat_session,
            summary,
            messages=messages,
            memories=memories,
        )
        result: dict[str, Any] = {
            "operation": "sessions.read",
            "intent": intent,
            "session": _session_payload(chat_session),
            "summary": summary_payload,
            "message_count": all_message_count,
            "returned_message_count": len(messages) if request.include_messages else 0,
            "message_limit": request.message_limit,
            "messages_truncated": truncated,
            "has_more_messages": truncated,
            "message_window": {
                "position": "latest",
                "returned_count": len(messages) if request.include_messages else 0,
                "total_count": all_message_count,
                "limit": request.message_limit,
                "has_more_before_window": truncated,
            },
            "memories_written": [_memory_payload(memory) for memory in memories],
        }
        if request.include_messages:
            result["messages"] = [_message_payload(message) for message in messages]

    return MemoryOperationResult(
        ok=True,
        result=result,
        cognitive_hint=(
            "This is episodic recall. Treat the transcript as stronger evidence "
            "than the summary when reconstructing what happened."
        ),
        suggested_next_actions=[
            "Use source_session_id from semantic memories to reach this transcript",
            "Write or update semantic memory only when the transcript reveals reusable durable context",
        ],
        confidence=0.96 if not truncated else 0.82,
    )


def handle_session_summarize(
    session_id: str,
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _context_required("sessions.summarize")
    try:
        request = SessionSummarizeBody.model_validate(body)
    except ValidationError as exc:
        return _validation_error("sessions.summarize", exc)

    with Session(context.engine) as db:
        chat_session = repositories.get_chat_session(db, session_id)
        if chat_session is None:
            return _session_not_found(session_id, operation="sessions.summarize")
        messages = repositories.list_messages(db, session_id=session_id)
        conversation_messages = _conversation_messages(messages)
        memories = repositories.list_memories_for_session(db, session_id=session_id)
        existing_summary = repositories.get_session_summary(db, session_id=session_id)
        last_message_id = (
            conversation_messages[-1].id if conversation_messages else None
        )
        if (
            existing_summary is not None
            and not request.force
            and existing_summary.last_message_id == last_message_id
            and existing_summary.message_count == len(conversation_messages)
        ):
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "sessions.summarize",
                    "session_id": session_id,
                    "up_to_date": True,
                    "summary": _summary_payload(existing_summary),
                    "memories_written": [_memory_payload(memory) for memory in memories],
                },
                cognitive_hint=(
                    "The existing episodic summary already covers the current transcript."
                ),
                suggested_next_actions=[
                    "Read the full session if exact details are needed",
                ],
                confidence=0.96,
            )

    if not conversation_messages:
        normalized = {
            "summary": "Empty session without user or assistant messages.",
            "topics": [],
            "decisions": [],
            "open_questions": [],
            "notable_context": [],
        }
        provider_payload = None
        repair_payload = None
        json_repair_applied = False
        summary_source = "deterministic_empty"
    else:
        if context.settings is None or context.provider_factory is None:
            return _provider_unavailable(
                "Session summarization requires an LLM provider in context."
            )
        try:
            provider = context.provider_factory(context.settings)
            result = provider.generate_text(
                prompt=_build_summary_prompt(
                    chat_session,
                    conversation_messages,
                    memories=memories,
                    focus=request.focus,
                ),
                system=SESSION_SUMMARY_SYSTEM_PROMPT,
                max_tokens=active_provider_max_tokens(context.settings),
            )
        except LLMConfigurationError as exc:
            return _provider_unavailable(str(exc))
        except LLMRequestError as exc:
            return MemoryOperationResult(
                ok=False,
                result={"operation": "sessions.summarize", "session_id": session_id},
                cognitive_hint="The episodic summarization LLM call failed.",
                suggested_next_actions=[
                    "Retry the session summary after the provider recovers",
                    "Use GET /mind/sessions/{session_id} to inspect the raw transcript",
                ],
                confidence=1.0,
                error_code="sessions.summary.provider_error",
                error_message=str(exc),
            )

        repair_result: Any | None = None
        parsed = _parse_json_object(result.text)
        if parsed is None:
            try:
                repair_result = provider.generate_text(
                    prompt=_build_repair_prompt(result.text),
                    system=SESSION_SUMMARY_REPAIR_SYSTEM_PROMPT,
                    max_tokens=active_provider_max_tokens(context.settings),
                )
                parsed = _parse_json_object(repair_result.text)
            except (LLMConfigurationError, LLMRequestError):
                repair_result = None

        if parsed is None:
            trace_id = _add_summary_trace(
                context,
                {
                    "operation": "sessions.summarize",
                    "intent": intent,
                    "session_id": session_id,
                    "provider": _provider_payload(result),
                    "repair_provider": _provider_payload(repair_result)
                    if repair_result is not None
                    else None,
                    "parse_error": "summary_not_json",
                },
            )
            return MemoryOperationResult(
                ok=False,
                result={
                    "operation": "sessions.summarize",
                    "session_id": session_id,
                    "raw_summary": result.text,
                    "trace_ids": [trace_id],
                },
                cognitive_hint=(
                    "The summarizer returned non-JSON output. Use the raw "
                    "transcript for now and retry summarization later."
                ),
                suggested_next_actions=[
                    "Retry POST /mind/sessions/{session_id}/summarize",
                    "Read the full session transcript",
                ],
                confidence=0.45,
                error_code="sessions.summary.invalid_json",
                error_message="Session summary was not valid JSON.",
            )

        normalized = _normalize_summary(parsed)
        provider_payload = _provider_payload(result)
        repair_payload = (
            _provider_payload(repair_result) if repair_result is not None else None
        )
        json_repair_applied = repair_result is not None
        summary_source = "llm"

    with Session(context.engine) as db:
        message_count = len(conversation_messages)
        source_turn_count = len(
            {
                message.turn_id
                for message in conversation_messages
                if message.turn_id is not None
            }
        )
        last_message_id = (
            conversation_messages[-1].id if conversation_messages else None
        )
        session_summary = repositories.upsert_session_summary(
            db,
            session_id=session_id,
            summary=normalized["summary"],
            topics=normalized["topics"],
            decisions=normalized["decisions"],
            open_questions=normalized["open_questions"],
            memory_ids=[memory.id for memory in memories],
            message_count=message_count,
            source_turn_count=source_turn_count,
            last_message_id=last_message_id,
            status="active",
            summary_version=SESSION_SUMMARY_VERSION,
            metadata={
                "summary_source": summary_source,
                "intent": intent,
                "focus": request.focus,
                "message_scope": "full_user_assistant_history",
                "notable_context": normalized["notable_context"],
                "json_repair_applied": json_repair_applied,
            },
        )
        trace_id = _add_summary_trace(
            context,
            {
                "operation": "sessions.summarize",
                "intent": intent,
                "session_id": session_id,
                "summary_id": session_summary.id,
                "input": request.model_dump(mode="json"),
                "summary": _summary_payload(session_summary),
                "provider": provider_payload,
                "repair_provider": repair_payload,
                "json_repair_applied": json_repair_applied,
            },
        )

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "sessions.summarize",
            "session_id": session_id,
            "up_to_date": False,
            "summary": _summary_payload(session_summary),
            "memories_written": [_memory_payload(memory) for memory in memories],
            "trace_ids": [trace_id],
            "json_repair_applied": json_repair_applied,
        },
        cognitive_hint=(
            "The session now has an episodic summary for navigation. The full "
            "transcript remains the source of truth for exact reconstruction."
        ),
        suggested_next_actions=[
            "Use GET /mind/sessions to find relevant sessions",
            "Use GET /mind/sessions/{session_id} when exact conversation evidence matters",
        ],
        confidence=0.9,
    )


def _context_required(operation: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": operation},
        cognitive_hint="Episodic recall requires session context so the call can be traced.",
        suggested_next_actions=["Retry with a valid session_id"],
        confidence=1.0,
        error_code="sessions.context_required",
        error_message="Episodic session recall requires traceable session context.",
    )


def _validation_error(operation: str, exc: ValidationError) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={
            "operation": operation,
            "validation_errors": exc.errors(),
            "expected_schema_hint": "Call GET /mind/schema for the episodic route body_schema.",
        },
        cognitive_hint="Retry the episodic route with the schema body shape.",
        suggested_next_actions=["Call GET /mind/schema", "Retry the session route"],
        confidence=1.0,
        error_code="sessions.invalid_body",
        error_message=str(exc),
    )


def _session_not_found(session_id: str, *, operation: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": operation, "session_id": session_id},
        cognitive_hint="No chat session with that id exists in the local store.",
        suggested_next_actions=["Call GET /mind/sessions to inspect available sessions"],
        confidence=1.0,
        error_code="sessions.not_found",
        error_message=f"Session {session_id} was not found.",
    )


def _provider_unavailable(message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": "sessions.summarize"},
        cognitive_hint="The LLM-backed episodic summarizer is unavailable.",
        suggested_next_actions=[
            "Read the exact session transcript",
            "Retry summarization after provider configuration is available",
        ],
        confidence=1.0,
        error_code="sessions.summary.provider_unavailable",
        error_message=message,
    )


def _session_index_payload(
    db: Session,
    chat_session: ChatSession,
    *,
    sparse_match: Any | None = None,
) -> dict[str, Any]:
    summary = repositories.get_session_summary(db, session_id=chat_session.id)
    memories = repositories.list_memories_for_session(db, session_id=chat_session.id)
    messages = repositories.list_messages(db, session_id=chat_session.id)
    payload = {
        **_session_payload(chat_session),
        "summary": _summary_or_fallback_payload(
            chat_session,
            summary,
            messages=messages,
            memories=memories,
        ),
        "memory_ids": [memory.id for memory in memories],
    }
    if sparse_match is not None:
        payload["score"] = round(sparse_match.score, 4)
        payload["why_relevant"] = sparse_match.why_relevant
    return payload


def _summary_or_fallback_payload(
    chat_session: ChatSession,
    summary: SessionSummary | None,
    *,
    messages: list[Message],
    memories: list[MemoryRecord],
) -> dict[str, Any]:
    if summary is not None:
        return _summary_payload(summary)
    fallback = _fallback_summary(chat_session, messages)
    return {
        "id": None,
        "session_id": chat_session.id,
        "summary": fallback,
        "topics": [],
        "decisions": [],
        "open_questions": [],
        "memory_ids": [memory.id for memory in memories],
        "message_count": len(messages),
        "source_turn_count": len(
            {
                message.turn_id
                for message in messages
                if message.turn_id is not None
            }
        ),
        "last_message_id": messages[-1].id if messages else None,
        "status": "fallback",
        "summary_version": SESSION_SUMMARY_VERSION,
        "metadata": {"summary_source": "deterministic_fallback"},
        "created_at": None,
        "updated_at": None,
    }


def _summary_payload(summary: SessionSummary) -> dict[str, Any]:
    return {
        "id": summary.id,
        "session_id": summary.session_id,
        "summary": summary.summary,
        "topics": summary.topics_json,
        "decisions": summary.decisions_json,
        "open_questions": summary.open_questions_json,
        "memory_ids": summary.memory_ids_json,
        "message_count": summary.message_count,
        "source_turn_count": summary.source_turn_count,
        "last_message_id": summary.last_message_id,
        "status": summary.status,
        "summary_version": summary.summary_version,
        "metadata": summary.metadata_json,
        "created_at": _isoformat(summary.created_at),
        "updated_at": _isoformat(summary.updated_at),
    }


def _session_payload(chat_session: ChatSession) -> dict[str, Any]:
    return {
        "id": chat_session.id,
        "title": chat_session.title,
        "created_at": _isoformat(chat_session.created_at),
        "updated_at": _isoformat(chat_session.updated_at),
        "metadata": chat_session.metadata_json,
    }


def _message_payload(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "turn_id": message.turn_id,
        "role": message.role,
        "content": message.content,
        "created_at": _isoformat(message.created_at),
        "metadata": message.metadata_json,
    }


def _memory_payload(memory: MemoryRecord) -> dict[str, Any]:
    return {
        "id": memory.id,
        "type": memory.memory_type,
        "scope": memory.scope,
        "status": memory.status,
        "content": memory.content,
        "reason_for_storage": memory.reason_for_storage,
        "expected_future_use": memory.expected_future_use,
        "confidence": memory.confidence,
        "salience": memory.salience,
        "source_session_id": memory.source_session_id,
        "source_turn_id": memory.source_turn_id,
        "source_message_id": memory.source_message_id,
        "tags": memory.tags_json,
        "usage_count": memory.usage_count,
        "created_at": _isoformat(memory.created_at),
        "updated_at": _isoformat(memory.updated_at),
    }


def _fallback_summary(chat_session: ChatSession, messages: list[Message]) -> str:
    if not messages:
        return "Empty session without user or assistant messages."
    first_user = next((message.content for message in messages if message.role == "user"), "")
    last_message = messages[-1].content
    title = chat_session.title or "Untitled session"
    return (
        f"{title}. {len(messages)} messages. "
        f"First user message: {_truncate(first_user, 180)} "
        f"Last message: {_truncate(last_message, 220)}"
    )


def _session_matches_query(
    db: Session,
    chat_session: ChatSession,
    query: str,
) -> bool:
    summary = repositories.get_session_summary(db, session_id=chat_session.id)
    messages = repositories.list_messages(db, session_id=chat_session.id)
    text_parts = [
        chat_session.title or "",
        summary.summary if summary is not None else "",
        " ".join(summary.topics_json if summary is not None else []),
        " ".join(summary.decisions_json if summary is not None else []),
        " ".join(summary.open_questions_json if summary is not None else []),
        " ".join(message.content for message in messages[-4:]),
    ]
    haystack = " ".join(text_parts).casefold()
    tokens = [token for token in query.casefold().split() if token]
    return all(token in haystack for token in tokens)


def _filter_sessions_by_time(
    db: Session,
    sessions: list[ChatSession],
    *,
    time_filter: TimeFilter | None,
    resolved_time: dict[str, Any] | None,
    context: MindAPIContext,
) -> list[ChatSession]:
    if time_filter is None:
        return sessions
    if time_filter.preset == "this_session":
        return [
            chat_session
            for chat_session in sessions
            if chat_session.id == context.session_id
        ]
    basis = time_filter.basis or "conversation"
    return [
        chat_session
        for chat_session in sessions
        if _session_matches_time(
            db,
            chat_session,
            basis=basis,
            resolved_time=resolved_time,
        )
    ]


def _session_matches_time(
    db: Session,
    chat_session: ChatSession,
    *,
    basis: str,
    resolved_time: dict[str, Any] | None,
) -> bool:
    if basis == "created":
        return interval_contains(chat_session.created_at, resolved=resolved_time)
    if basis == "updated":
        return interval_contains(chat_session.updated_at, resolved=resolved_time)
    if basis == "summary":
        summary = repositories.get_session_summary(db, session_id=chat_session.id)
        if summary is None:
            return interval_contains(chat_session.updated_at, resolved=resolved_time)
        return interval_contains(summary.updated_at, resolved=resolved_time)
    messages = [
        message
        for message in repositories.list_messages(db, session_id=chat_session.id)
        if message.role in {"user", "assistant"}
    ]
    if not messages:
        return interval_contains(chat_session.created_at, resolved=resolved_time)
    return any(
        interval_contains(message.created_at, resolved=resolved_time)
        for message in messages
    )


def _build_summary_prompt(
    chat_session: ChatSession,
    messages: list[Message],
    *,
    memories: list[MemoryRecord],
    focus: str | None,
) -> str:
    transcript = _render_transcript(messages)
    payload = {
        "session": _session_payload(chat_session),
        "focus": focus,
        "messages_included": len(messages),
        "message_scope": "full_user_assistant_history",
        "memories_written_from_session": [_memory_payload(memory) for memory in memories],
        "transcript": transcript,
    }
    return (
        "Compact this full user<->assistant session into Scarlet's episodic memory index. "
        "Return only JSON.\n\n"
        + json.dumps(payload, ensure_ascii=True, indent=2)
    )


def _render_transcript(messages: list[Message]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for message in messages:
        rendered.append(
            {
                "id": message.id,
                "turn_id": message.turn_id,
                "role": message.role,
                "content": message.content,
                "created_at": _isoformat(message.created_at),
            }
        )
    return rendered


def _conversation_messages(messages: list[Message]) -> list[Message]:
    return [
        message
        for message in messages
        if message.role in {"user", "assistant"}
    ]


def _build_repair_prompt(raw_summary: str) -> str:
    return (
        "Repair this malformed internal session summary into valid JSON matching "
        "the required summary schema. Return only JSON.\n\n"
        + raw_summary
    )


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_summary(parsed: dict[str, Any]) -> dict[str, Any]:
    summary = _string(parsed.get("summary")) or "Session summary generated."
    return {
        "summary": summary[:4000],
        "topics": _list_of_strings(parsed.get("topics"))[:12],
        "decisions": _list_of_strings(parsed.get("decisions"))[:12],
        "open_questions": _list_of_strings(parsed.get("open_questions"))[:12],
        "notable_context": _list_of_strings(parsed.get("notable_context"))[:12],
    }


def _add_summary_trace(context: MindAPIContext, payload: dict[str, Any]) -> str:
    with Session(context.engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=context.session_id or "",
            turn_id=context.turn_id,
            kind="mind.sessions.summarize",
            payload=payload,
        )
        return trace.id


def _provider_payload(result: Any) -> dict[str, Any]:
    return {
        "model": result.model,
        "usage": result.usage,
        "provider_message_id": result.provider_message_id,
        "stop_reason": result.stop_reason,
        "raw_text": result.text,
    }


def _normalized_query(query: str | None) -> str | None:
    if not isinstance(query, str):
        return None
    stripped = query.strip()
    return stripped or None


def _string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None
