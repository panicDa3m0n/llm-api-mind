"""Shared immutable baseline metadata and copy guards for evaluator suites."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.storage.models import ChatSession, MemoryFact, MemoryRecord


BASELINE_LFS_OID = "827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5"
BASELINE_COUNTS = {
    "memories": 34,
    "memory_facts": 25,
    "sessions": 155,
    "messages": 567,
    "focus_records": 0,
    "intention_records": 0,
    "affect_states": 0,
}


@dataclass(frozen=True)
class FrozenReference:
    name: str
    memory_id: str
    source_session_id: str
    fact_id: str | None
    status: str
    required_terms: tuple[str, ...]


FROZEN_REFERENCES = {
    "zero_luce_active": FrozenReference(
        name="active Zero-Luce protocol",
        memory_id="mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",
        source_session_id="ses_24fbc3a0722d4010b7bde8f74496ef69",
        fact_id="fact_75db0c43231047c0bf4e66d6c5ba2c3a",
        status="active",
        required_terms=("Protocollo Zero-Luce", "Rischio", "Prossima azione"),
    ),
    "zero_luce_deprecated": FrozenReference(
        name="deprecated Zero-Luce predecessor",
        memory_id="mem_abed5590f91b4eb8aa93d1103db024de",
        source_session_id="ses_421dd143a25840adb317ef2afd2c2e9c",
        fact_id="fact_f35cda893b584765a25cffdfc2ae30d8",
        status="deprecated",
        required_terms=("Protocollo Zero-Luce", "tre blocchi"),
    ),
    "episodic_bridge": FrozenReference(
        name="semantic-to-episodic bridge decision",
        memory_id="mem_06ef7093f3e74f099c77d6f356f67d26",
        source_session_id="ses_8f9145b9ca5a4aa78534936dac03a8d5",
        fact_id="fact_0f96f4c04c654d178e64195b5a81e239",
        status="active",
        required_terms=("semantic", "source_session_id", "episodic"),
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_frozen_baseline(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Frozen baseline missing: {path}")
    actual = sha256_file(path)
    if actual != BASELINE_LFS_OID:
        raise RuntimeError(
            f"Frozen baseline hash mismatch: expected {BASELINE_LFS_OID}, got {actual}."
        )


def prepare_disposable_copy(*, baseline_db: Path, run_db: Path, marker: str) -> None:
    assert_frozen_baseline(baseline_db)
    resolved = run_db.resolve()
    if marker not in resolved.name or resolved.suffix != ".db":
        raise RuntimeError(f"Refusing unsafe evaluator database target: {run_db}")
    if resolved == baseline_db.resolve():
        raise RuntimeError("Evaluator database must differ from the frozen baseline.")
    run_db.parent.mkdir(parents=True, exist_ok=True)
    if run_db.exists():
        run_db.unlink()
    shutil.copy2(baseline_db, run_db)


def verify_frozen_references(db: Session) -> dict[str, Any]:
    counts = {
        "memories": len(db.exec(select(MemoryRecord)).all()),
        "memory_facts": len(db.exec(select(MemoryFact)).all()),
        "sessions": len(db.exec(select(ChatSession)).all()),
        "messages": _table_count(db, "messages"),
        "focus_records": _table_count(db, "focus_records"),
        "intention_records": _table_count(db, "intention_records"),
        "affect_states": _table_count(db, "affect_states"),
    }
    if counts != BASELINE_COUNTS:
        raise RuntimeError(f"Frozen baseline inventory changed: {counts}")

    resolved: dict[str, Any] = {}
    for key, reference in FROZEN_REFERENCES.items():
        memory = db.get(MemoryRecord, reference.memory_id)
        if memory is None:
            raise RuntimeError(f"Missing frozen memory reference {reference.memory_id}")
        if memory.status != reference.status:
            raise RuntimeError(
                f"{reference.memory_id} status {memory.status!r} != {reference.status!r}"
            )
        if memory.source_session_id != reference.source_session_id:
            raise RuntimeError(f"{reference.memory_id} source session changed")
        for term in reference.required_terms:
            if term.casefold() not in memory.content.casefold():
                raise RuntimeError(f"{reference.memory_id} missing term {term!r}")
        if db.get(ChatSession, reference.source_session_id) is None:
            raise RuntimeError(f"Missing source session {reference.source_session_id}")
        if reference.fact_id is not None:
            fact = db.get(MemoryFact, reference.fact_id)
            if fact is None or fact.memory_id != reference.memory_id:
                raise RuntimeError(f"Missing frozen fact reference {reference.fact_id}")
        resolved[key] = asdict(reference)
    return {"counts": counts, "references": resolved}


def _table_count(db: Session, table: str) -> int:
    result = db.connection().exec_driver_sql(f"SELECT COUNT(*) FROM {table}")
    return int(result.scalar_one())
