import base64
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from app.config import Settings
from app.mind.contracts import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.research_lab.runner import RunnerArtifact, RunnerExecution
from app.research_lab.web import (
    ResearchLabWebError,
    WebDocument,
    fetch_public_web_document,
)
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import (
    MemoryRecord,
    ResearchLabArtifact,
    ResearchLabRun,
    ResearchLabSource,
)


def _context(db_engine, *, enabled: bool = True) -> MindAPIContext:
    init_db(db_engine)
    with Session(db_engine) as db:
        session = repositories.create_chat_session(db, title="Research Lab test")
    return MindAPIContext(
        engine=db_engine,
        session_id=session.id,
        turn_id="turn_lab_test",
        settings=Settings(
            environment="test",
            minimax_api_key="test-key",
            research_lab_enabled=enabled,
            research_lab_runner_uds="/tmp/research-lab-test.sock" if enabled else None,
        ),
    )


def test_lab_is_operator_gated_and_never_claims_disabled_access(db_engine) -> None:
    response = dispatch_mind_shell(
        MindShellRequest(command="lab status", intent="Inspect laboratory availability."),
        context=_context(db_engine, enabled=False),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "lab.disabled"
    assert "not accessed" in response.error.message


def test_lab_aliases_and_config_limits_follow_the_runner_contract(db_engine) -> None:
    response = dispatch_mind_shell(
        MindShellRequest(command="lab info", intent="Inspect laboratory availability."),
        context=_context(db_engine),
    )

    assert response.ok is True
    assert response.result["target"] == "lab.status"
    assert response.result["data"]["availability"]["python"] == "runner_configured"

    with pytest.raises(ValidationError, match="less than or equal to 12000"):
        Settings(
            environment="test",
            minimax_api_key="test-key",
            research_lab_code_max_chars=12_001,
        )


def test_lab_python_persists_a_source_labelled_receipt_and_artifact(
    db_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(db_engine)
    captured: dict = {}

    def fake_execute_python(*, settings, code: str, sources: list[dict[str, str]]):
        captured["code"] = code
        captured["sources"] = sources
        return RunnerExecution(
            status="completed",
            stdout="x**2 + 2*x + 1\n",
            stderr="",
            exit_code=0,
            timed_out=False,
            artifacts=[
                RunnerArtifact(
                    name="result.txt",
                    media_type="text/plain",
                    content_base64=base64.b64encode(b"verified artifact").decode("ascii"),
                    sha256="a" * 64,
                )
            ],
            source_paths={},
            runner_identity="fake-runner-v1",
        )

    monkeypatch.setattr("app.mind.research_lab.execute_python", fake_execute_python)
    response = dispatch_mind_shell(
        MindShellRequest(
            command=(
                'lab python --code "from sympy import expand; print(expand((x + 1)**2))"'
            ),
            intent="Verify a symbolic expansion before answering.",
        ),
        context=context,
    )

    assert response.ok is True
    assert response.result["target"] == "lab.python"
    data = response.result["data"]
    assert data["output"]["stdout"] == "x**2 + 2*x + 1\n"
    assert captured["sources"] == []
    run_id = data["run"]["id"]
    artifact_id = data["artifacts"][0]["id"]

    opened = dispatch_mind_shell(
        MindShellRequest(command=f"lab run {run_id}"),
        context=context,
    )
    artifact = dispatch_mind_shell(
        MindShellRequest(command=f"lab artifact {artifact_id}"),
        context=context,
    )
    assert opened.ok is True
    assert opened.result["data"]["run"]["request"]["code_sha256"]
    assert artifact.ok is True
    assert artifact.result["data"]["artifact"]["text"] == "verified artifact"

    with Session(db_engine) as db:
        assert len(list(db.exec(select(ResearchLabRun)).all())) == 1
        assert len(list(db.exec(select(ResearchLabArtifact)).all())) == 1
        assert list(db.exec(select(ResearchLabSource)).all()) == []


def test_lab_web_source_is_explicit_and_can_be_provided_to_python(
    db_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(db_engine)

    def fake_fetch(*_args, **_kwargs) -> WebDocument:
        return WebDocument(
            url="https://example.org/reference",
            title="Reference",
            content="A source-backed value is 42.",
            content_type="text/plain",
            retrieved_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
            byte_size=29,
            content_sha256="b" * 64,
        )

    captured: dict = {}

    def fake_execute_python(*, settings, code: str, sources: list[dict[str, str]]):
        captured["sources"] = sources
        return RunnerExecution(
            status="completed",
            stdout="42\n",
            stderr="",
            exit_code=0,
            timed_out=False,
            artifacts=[],
            source_paths={sources[0]["id"]: "sources/source_0.txt"},
            runner_identity="fake-runner-v1",
        )

    monkeypatch.setattr("app.mind.research_lab.fetch_public_web_document", fake_fetch)
    monkeypatch.setattr("app.mind.research_lab.execute_python", fake_execute_python)
    fetched = dispatch_mind_shell(
        MindShellRequest(
            command='lab web open "https://example.org/reference"',
            intent="Read a cited public document.",
        ),
        context=context,
    )
    assert fetched.ok is True
    source_id = fetched.result["data"]["source"]["id"]
    assert "content" not in fetched.result["data"]["source"]

    source = dispatch_mind_shell(
        MindShellRequest(command=f"lab source {source_id}"),
        context=context,
    )
    assert source.ok is True
    assert source.result["data"]["source"]["content"] == "A source-backed value is 42."

    computation = dispatch_mind_shell(
        MindShellRequest(
            command=f'lab python --source {source_id} --code "print(42)"',
            intent="Process the explicitly opened source.",
        ),
        context=context,
    )
    assert computation.ok is True
    assert captured["sources"] == [
        {"id": source_id, "content": "A source-backed value is 42."}
    ]
    with Session(db_engine) as db:
        assert list(db.exec(select(MemoryRecord)).all()) == []


def test_public_web_fetch_rejects_private_networks_and_bounds_html() -> None:
    def public_resolver(*_args, **_kwargs):
        return [(None, None, None, None, ("93.184.216.34", 443))]

    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=(
                    "<html><head><title>Source title</title></head>"
                    "<body><script>ignored()</script><p>Useful text</p></body></html>"
                ),
            )
        )
    )
    document = fetch_public_web_document(
        "https://example.org/document",
        timeout_seconds=1,
        max_bytes=10_000,
        max_chars=1_000,
        client=client,
        resolver=public_resolver,
    )
    assert document.title == "Source title"
    assert document.content == "Useful text"

    bounded = fetch_public_web_document(
        "https://example.org/document",
        timeout_seconds=1,
        max_bytes=10_000,
        max_chars=20,
        client=client,
        resolver=public_resolver,
    )
    assert len(bounded.content) <= 20

    def private_resolver(*_args, **_kwargs):
        return [(None, None, None, None, ("127.0.0.1", 443))]

    with pytest.raises(ResearchLabWebError, match="Private or local"):
        fetch_public_web_document(
            "https://localhost/secret",
            timeout_seconds=1,
            max_bytes=10_000,
            max_chars=1_000,
            client=client,
            resolver=private_resolver,
        )
