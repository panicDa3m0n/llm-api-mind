from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.config import Settings
from app.llm.provider import LLMMessage, LLMStreamEvent, LLMTextResult
from app.main import create_app
from app.mind.search import sync_session_documents
from app.storage import repositories
from app.storage.db import create_db_engine, init_db, prepare_runtime_database
from app.storage.models import (
    ChatSession,
    EmbeddingVector,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryRecord,
    MemorySurface,
    SessionSummary,
)


DATASET_VERSION = "codex-memory-eval-v2"
DEFAULT_SOURCE_DB = "data/preliminary-rework-v1.db"
DEFAULT_RUN_DB = "data/codex-memory-eval-v2-run.db"
UTC = timezone.utc


@dataclass(frozen=True)
class MemorySpec:
    key: str
    memory_type: str
    scope: str
    content: str
    reason: str
    future_use: str
    tags: tuple[str, ...]
    confidence: float = 0.86
    salience: float = 0.76
    lane: str = "generated"


@dataclass(frozen=True)
class EvalCase:
    name: str
    query: str
    scope: str | None
    expected_keys: tuple[str, ...]
    forbidden_keys: tuple[str, ...] = ()
    top_k: int = 10


@dataclass(frozen=True)
class ContextEvalCase:
    name: str
    user_message: str
    expected_keys: tuple[str, ...] = ()
    expected_content_terms: tuple[str, ...] = ()
    forbidden_content_terms: tuple[str, ...] = ()
    max_selected_count: int | None = None
    expected_behavior: str = ""


class ContextProbeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=self.settings.minimax_model,
            text="context probe text",
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=self.settings.minimax_model,
            text="Context probe completed.",
            usage={"input_tokens": len(messages), "output_tokens": 4},
            raw_content=[{"type": "text", "text": "Context probe completed."}],
            stop_reason="end_turn",
        )

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        return self.generate_chat(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
        )

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ):
        result = self.generate_chat(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
        )
        yield LLMStreamEvent(type="text_delta", data={"text": result.text})
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def main() -> None:
    args = _parse_args()
    root = Path(__file__).resolve().parents[2]
    source_db = _resolve(root, args.source_db)
    run_db = _resolve(root, args.run_db)
    _prepare_run_database(
        source_db=source_db,
        run_db=run_db,
        reuse=args.reuse_run,
    )

    settings = _settings(source_db=source_db, run_db=run_db)
    database_url = prepare_runtime_database(settings)
    engine = create_db_engine(database_url)
    init_db(engine)
    client = TestClient(create_app(settings, db_engine=engine))
    context_client = TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda settings: ContextProbeProvider(settings),
            db_engine=engine,
        )
    )

    before = _count_state(engine)
    health = client.get("/health").json()
    dataset = _build_dataset(args.target_count)
    session_ids = _ensure_source_sessions(engine)
    write_report = _write_dataset(client, dataset, session_ids=session_ids)
    lifecycle_report = _write_lifecycle_pair(client, session_ids=session_ids)
    after_population = _count_state(engine)
    eval_report = _run_eval_cases(client, _eval_cases())
    context_eval_report = _run_context_eval_cases(
        context_client,
        _context_eval_cases(),
    )
    after_eval = _count_state(engine)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": DATASET_VERSION,
        "source_db": str(source_db),
        "run_db": str(run_db),
        "codex_test_database_url": database_url,
        "health_database": health.get("database"),
        "counts": {
            "before": before,
            "after_population": after_population,
            "after_eval": after_eval,
        },
        "writes": write_report,
        "lifecycle": lifecycle_report,
        "eval": eval_report,
        "context_eval": context_eval_report,
    }
    _write_report(report)
    print(json.dumps(report, ensure_ascii=True, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed and evaluate the isolated Codex memory test database."
    )
    parser.add_argument(
        "--source-db",
        default=DEFAULT_SOURCE_DB,
        help="Frozen or deliberately chosen laboratory source to copy without mutation.",
    )
    parser.add_argument(
        "--run-db",
        default=DEFAULT_RUN_DB,
        help="Disposable evaluation copy. Its name must contain 'codex-memory-eval'.",
    )
    parser.add_argument(
        "--reuse-run",
        action="store_true",
        help="Reuse an existing disposable evaluation DB instead of recreating it.",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=240,
        help="Approximate number of generated memories to add before lifecycle extras.",
    )
    return parser.parse_args()


def _settings(*, source_db: Path, run_db: Path) -> Settings:
    settings = Settings(
        environment="evaluation",
        database_role="test",
        codex_test=True,
        database_url=f"sqlite:///{source_db}",
        codex_test_database_url=f"sqlite:///{run_db}",
        codex_test_seed_database_url=f"sqlite:///{source_db}",
        maintenance_enabled=False,
        retrieval_shadow_enabled=True,
        retrieval_shadow_backend="openrouter",
        retrieval_shadow_cloud_surface_limit=160,
        retrieval_shadow_rerank_enabled=True,
        retrieval_shadow_rerank_candidate_limit=40,
        retrieval_shadow_rerank_top_n=10,
        retrieval_hybrid_mode="active",
    )
    if not settings.openrouter_api_key:
        settings.retrieval_shadow_backend = "local"
        settings.retrieval_shadow_rerank_enabled = False
    return settings


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _prepare_run_database(*, source_db: Path, run_db: Path, reuse: bool) -> None:
    if not source_db.exists():
        raise RuntimeError(f"Evaluation source database does not exist: {source_db}")
    if "codex-memory-eval" not in run_db.name:
        raise RuntimeError(
            "Refusing to create or remove a run database without the "
            "'codex-memory-eval' marker."
        )
    if run_db.exists() and not reuse:
        run_db.unlink()
    if not run_db.exists():
        run_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, run_db)


def _ensure_source_sessions(engine: Engine) -> dict[str, str]:
    sessions = {
        "user": {
            "title": "Codex Test Seed - user preferences",
            "summary": (
                "Controlled Codex test memories about user preferences, wellbeing, "
                "food, communication, privacy, and personal continuity."
            ),
            "topics": ["user preferences", "wellbeing", "communication", "privacy"],
        },
        "project": {
            "title": "Codex Test Seed - project and API Mind",
            "summary": (
                "Controlled Codex test memories about API Mind, Scarlet project "
                "decisions, workflows, retrieval, and system behavior."
            ),
            "topics": ["api mind", "workflow", "retrieval", "project"],
        },
        "metacognition": {
            "title": "Codex Test Seed - metacognitive lessons",
            "summary": (
                "Controlled Codex test memories about Scarlet self-monitoring, "
                "effort routing, lessons, drift, and answer discipline."
            ),
            "topics": ["metacognition", "lessons", "effort routing"],
        },
    }
    session_ids: dict[str, str] = {}
    with Session(engine) as db:
        for lane, payload in sessions.items():
            existing = db.exec(
                select(ChatSession).where(ChatSession.title == payload["title"])
            ).first()
            if existing is None:
                existing = repositories.create_chat_session(
                    db,
                    title=payload["title"],
                    metadata={
                        "codex_test_dataset_version": DATASET_VERSION,
                        "lane": lane,
                    },
                )
                repositories.add_message(
                    db,
                    session_id=existing.id,
                    role="user",
                    content=f"Seed context for {payload['title']}.",
                    metadata={"codex_test_dataset_version": DATASET_VERSION},
                )
                repositories.add_message(
                    db,
                    session_id=existing.id,
                    role="assistant",
                    content=payload["summary"],
                    metadata={"codex_test_dataset_version": DATASET_VERSION},
                )
                repositories.upsert_session_summary(
                    db,
                    session_id=existing.id,
                    summary=payload["summary"],
                    topics=payload["topics"],
                    decisions=[],
                    open_questions=[],
                    message_count=2,
                    source_turn_count=0,
                    metadata={"codex_test_dataset_version": DATASET_VERSION},
                )
            session_ids[lane] = existing.id
        sync_session_documents(db, db.exec(select(ChatSession)).all())
    return session_ids


def _build_dataset(target_count: int) -> list[MemorySpec]:
    specs = list(_anchor_specs())
    generators = [
        _food_specs,
        _communication_specs,
        _project_specs,
        _metacognition_specs,
        _operations_specs,
        _distractor_specs,
    ]
    index = 0
    while len(specs) < target_count:
        for generator in generators:
            specs.append(generator(index))
            if len(specs) >= target_count:
                break
        index += 1
    return specs[:target_count]


def _anchor_specs() -> tuple[MemorySpec, ...]:
    return (
        MemorySpec(
            key="ct_food_chocolate_limit",
            memory_type="user_preference",
            scope="user",
            content=(
                "Davide adora il cioccolato, ma non puo mangiarne troppo: quando "
                "supera il suo limite personale sta male. Le proposte su dolci, "
                "comfort food o bevande serali devono tenerne conto."
            ),
            reason=(
                "Vincolo personale stabile su gusto e benessere, utile in future "
                "raccomandazioni alimentari."
            ),
            future_use=(
                "Usare quando si parla di cioccolato, dessert, bevande serali, "
                "comfort food o compromessi tra piacere e benessere."
            ),
            tags=("food", "chocolate", "wellbeing", "personal-limit"),
            salience=0.9,
            lane="user",
        ),
        MemorySpec(
            key="ct_food_evening_no_caffeine",
            memory_type="user_preference",
            scope="user",
            content=(
                "Davide sta riducendo la caffeina dopo cena per proteggere il "
                "sonno. Quando chiede bevande serali, Scarlet dovrebbe preferire "
                "opzioni senza caffeina salvo richiesta esplicita contraria."
            ),
            reason="Preferenza serale stabile collegata a sonno, energia e focus.",
            future_use=(
                "Usare per bevande serali, lavoro notturno, qualita del sonno, "
                "caffe, te, mate, cola e stimolanti."
            ),
            tags=("food", "drink", "caffeine", "sleep", "evening"),
            salience=0.92,
            lane="user",
        ),
        MemorySpec(
            key="ct_comm_brief_when_tired",
            memory_type="user_preference",
            scope="user",
            content=(
                "Quando Davide e stanco o lavora tardi, preferisce risposte "
                "asciutte, concise e dirette, senza lunghi preamboli."
            ),
            reason="Preferenza comunicativa stabile in contesti di stanchezza o lavoro serale.",
            future_use="Applicare a lavoro serale, segnali di fatica e risposte valutative.",
            tags=("communication", "brevity", "fatigue", "style"),
            salience=0.88,
            lane="user",
        ),
        MemorySpec(
            key="ct_comm_evening_report_three_sections",
            memory_type="user_preference",
            scope="user",
            content=(
                "Per audit serali o revisioni di lavoro, Davide preferisce spesso "
                "una struttura in tre sezioni: Coerenza, Evidenze, Debolezze."
            ),
            reason="Preferenza stabile di formato per sessioni valutative.",
            future_use="Usare quando Davide chiede analisi serali, audit o riepiloghi valutativi.",
            tags=("communication", "report-format", "evening", "audit"),
            salience=0.84,
            lane="user",
        ),
        MemorySpec(
            key="ct_meta_effort_routing_simple_requests",
            memory_type="behavioral_pattern",
            scope="project",
            content=(
                "Scarlet deve classificare il livello della richiesta prima di "
                "ragionare troppo: un saluto, una conferma diretta o una risposta "
                "a basso impatto non devono attivare indagini multi-step pesanti."
            ),
            reason="Lezione metacognitiva emersa dai test su over-processing di MiniMax M3.",
            future_use=(
                "Usare prima di rispondere a richieste semplici o dirette per "
                "evitare carico cognitivo inutile."
            ),
            tags=("metacognition", "effort-routing", "m3", "overprocessing"),
            salience=0.9,
            lane="metacognition",
        ),
        MemorySpec(
            key="ct_meta_schema_error_recovery",
            memory_type="behavioral_pattern",
            scope="project",
            content=(
                "Quando una chiamata API Mind fallisce per parametri errati, "
                "Scarlet deve leggere la guida d'errore dell'endpoint e riprovare "
                "con lo schema corretto invece di indovinare."
            ),
            reason="Regola metacognitiva operativa per affidabilita di API Mind.",
            future_use="Usare dopo errori di validazione, shape errata o route sbagliata di API Mind.",
            tags=("metacognition", "api-mind", "schema", "error-recovery"),
            salience=0.87,
            lane="metacognition",
        ),
        MemorySpec(
            key="ct_project_schema_first_unknown_endpoint",
            memory_type="project_fact",
            scope="project",
            content=(
                "Lo schema API Mind e la fonte di verita sugli endpoint disponibili. "
                "Scarlet deve consultarlo quando forma, parametri o disponibilita "
                "di un endpoint sono incerti."
            ),
            reason="Regola progettuale per evitare route API inventate.",
            future_use="Usare prima di operazioni API Mind non familiari e dopo errori API.",
            tags=("api-mind", "schema", "tool-use", "source-of-truth"),
            salience=0.9,
            lane="project",
        ),
        MemorySpec(
            key="ct_project_memory_to_session_bridge",
            memory_type="project_fact",
            scope="project",
            content=(
                "Le memorie semantiche sono ancore. Quando serve contesto storico "
                "preciso, Scarlet deve usare il source_session_id della memoria "
                "per aprire la sessione episodica di provenienza."
            ),
            reason="Regola centrale dell'architettura memoria semantica + episodica.",
            future_use="Usare quando deve verificare cosa e accaduto in una sessione passata.",
            tags=("memory", "episodic", "source-session", "architecture"),
            salience=0.91,
            lane="project",
        ),
        MemorySpec(
            key="ct_privacy_profile_scope",
            memory_type="project_fact",
            scope="project",
            content=(
                "Profilo utente, privacy scope, lingua, luogo e timezone sono dati "
                "operativi del runtime di Scarlet, non etichette cosmetiche."
            ),
            reason="Decisione progettuale per privacy multiutente e gestione contesto.",
            future_use="Usare quando si ragiona su impostazioni, profilo, privacy e localizzazione.",
            tags=("privacy", "profile", "runtime-context", "settings"),
            salience=0.84,
            lane="project",
        ),
        MemorySpec(
            key="ct_ops_world_action_boundary",
            memory_type="decision",
            scope="project",
            content=(
                "L'operativita esterna di Scarlet deve passare da capacita esplicite "
                "e tracciabili. Azioni reali nascoste o silenziose non rientrano "
                "nel comportamento accettabile attuale."
            ),
            reason="Decisione di governance per futuri strumenti operativi.",
            future_use="Usare prima di progettare azioni, plugin, operazioni filesystem o API esterne.",
            tags=("operations", "governance", "traceability", "future-tools"),
            salience=0.82,
            lane="project",
        ),
    )


def _food_specs(index: int) -> MemorySpec:
    foods = [
        ("infuso allo zenzero", "digestione serale calda"),
        ("te alla menta", "gusto fresco dopo cena"),
        ("latte d'avena", "alternativa delicata ai latticini"),
        ("acqua frizzante", "ristoro leggero"),
        ("fragole", "pianificazione di un dessert alla frutta"),
        ("pane scuro", "energia lenta a colazione"),
        ("mandorle", "piccolo snack prima di programmare"),
        ("salsa piccante", "sapore forte ma non prima di dormire"),
    ]
    item, context = foods[index % len(foods)]
    return MemorySpec(
        key=f"ct_food_distractor_{index:03d}",
        memory_type="user_preference",
        scope="user",
        content=(
            f"Nota alimentare controllata {index}: Davide ha citato {item} in "
            f"relazione a {context}. E una preferenza leggera, non una regola "
            "di salute."
        ),
        reason="Distrattore controllato di dominio alimentare per calibrare il retrieval.",
        future_use="Usare solo quando compare quel cibo o un contesto dietetico vicino.",
        tags=("food", "distractor", item.replace(" ", "-")),
        confidence=0.72,
        salience=0.48,
        lane="user",
    )


def _communication_specs(index: int) -> MemorySpec:
    styles = [
        "evitare di chiudere ogni risposta con una domanda",
        "preferire date concrete al tempo relativo quando il tempo conta",
        "tenere separata l'architettura speculativa dal comportamento implementato",
        "dichiarare i rischi residui senza drammatizzarli",
        "usare l'italiano di default salvo cambio lingua della piattaforma",
        "non usare ban di parole cablate come fix del comportamento LLM",
    ]
    style = styles[index % len(styles)]
    return MemorySpec(
        key=f"ct_comm_style_{index:03d}",
        memory_type="user_preference",
        scope="user",
        content=f"Nota comunicativa controllata {index}: Davide tende a {style}.",
        reason="Memoria controllata sullo stile comunicativo per calibrare il retrieval.",
        future_use=(
            "Usare quando contano stile della risposta, tono, riepiloghi "
            "valutativi o dialogo UX."
        ),
        tags=("communication", "style", "codex-test"),
        confidence=0.78,
        salience=0.55,
        lane="user",
    )


def _project_specs(index: int) -> MemorySpec:
    topics = [
        "blocchi runtime context",
        "compattazione dei pacchetti memoria",
        "superfici retrieval role-aware",
        "navigazione dei summary sessione",
        "inbox proposal di manutenzione",
        "superficie tool unica mind_api",
        "cache embedding OpenRouter",
        "retrieval associativo con grafo NetworkX",
    ]
    topic = topics[index % len(topics)]
    return MemorySpec(
        key=f"ct_project_fact_{index:03d}",
        memory_type="project_fact",
        scope="project",
        content=(
            f"Fatto progettuale controllato {index}: {topic} fa parte del runtime "
            "cognitivo di Scarlet e deve restare tracciabile prima di essere "
            "considerato affidabile."
        ),
        reason="Memoria controllata di dominio progetto per calibrare API Mind retrieval.",
        future_use="Usare quando si parla di architettura Scarlet, runtime, memoria o retrieval.",
        tags=("project", "api-mind", topic.replace(" ", "-")),
        confidence=0.8,
        salience=0.58,
        lane="project",
    )


def _metacognition_specs(index: int) -> MemorySpec:
    lessons = [
        "notare quando un'evidenza e solo un summary e aprire la fonte quando serve esattezza",
        "separare note pubbliche, thinking privato e risposta finale",
        "evitare di trattare una memoria recuperata come prova quando e solo un'ancora",
        "controllare se un'azione dichiarata e stata davvero eseguita",
        "ridurre lo sforzo quando l'evidenza e gia sufficiente",
        "salvare lezioni riutilizzabili come memoria semantica solo quando aiutano il comportamento futuro",
    ]
    lesson = lessons[index % len(lessons)]
    return MemorySpec(
        key=f"ct_meta_lesson_{index:03d}",
        memory_type="behavioral_pattern",
        scope="project",
        content=f"Lezione metacognitiva controllata {index}: Scarlet dovrebbe {lesson}.",
        reason="Lezione controllata per retrieval e routing futuro delle lezioni.",
        future_use="Usare quando Scarlet si monitora, valida o regola lo sforzo cognitivo.",
        tags=("metacognition", "lesson", "self-monitoring"),
        confidence=0.82,
        salience=0.62,
        lane="metacognition",
    )


def _operations_specs(index: int) -> MemorySpec:
    operations = [
        "scrivere codice tramite uno slice implementativo circoscritto",
        "avviare backend e frontend per test live",
        "leggere le trace prima di cambiare comportamento prompt",
        "duplicare lo stato DB prima di esperimenti memoria sporchi",
        "tenere separato confronto provider e regressioni di sistema",
        "eseguire test backend completi dopo modifiche storage ampie",
    ]
    operation = operations[index % len(operations)]
    return MemorySpec(
        key=f"ct_ops_workflow_{index:03d}",
        memory_type="task_context",
        scope="project",
        content=f"Workflow operativo controllato {index}: {operation}.",
        reason="Memoria controllata di workflow per retrieval operativo futuro.",
        future_use="Usare quando si pianifica implementazione, verifica o workflow valutativo.",
        tags=("operations", "workflow", "testing"),
        confidence=0.76,
        salience=0.54,
        lane="project",
    )


def _distractor_specs(index: int) -> MemorySpec:
    distractors = [
        "convenzioni astronomiche per nominare lune immaginarie",
        "note di giardinaggio su basilico e luce del balcone",
        "gusti musicali legati a tappeti synth ambient",
        "checklist bagagli per weekend piovosi",
        "preferenza per quaderni cartacei negli schizzi",
        "tolleranza al rumore degli switch tastiera in stanze condivise",
    ]
    item = distractors[index % len(distractors)]
    return MemorySpec(
        key=f"ct_far_distractor_{index:03d}",
        memory_type="project_fact" if index % 2 else "user_preference",
        scope="project" if index % 2 else "user",
        content=f"Distrattore lontano controllato {index}: {item}.",
        reason="Distrattore non correlato per calibrare controlli negativi.",
        future_use="Usare solo quando compare questo argomento non correlato.",
        tags=("far-distractor", "codex-test"),
        confidence=0.68,
        salience=0.42,
        lane="user" if index % 2 == 0 else "project",
    )


def _write_dataset(
    client: TestClient,
    dataset: list[MemorySpec],
    *,
    session_ids: dict[str, str],
) -> dict[str, Any]:
    created = 0
    deduplicated = 0
    failed: list[dict[str, Any]] = []
    keys: dict[str, str] = {}
    for spec in dataset:
        response = client.post(
            "/mind/call",
            json={
                "session_id": session_ids.get(spec.lane, session_ids["project"]),
                "method": "POST",
                "path": "/mind/memory/write",
                "intent": f"Codex test seed write for {spec.key}.",
                "body": {
                    "type": spec.memory_type,
                    "scope": spec.scope,
                    "content": spec.content,
                    "reason_for_storage": spec.reason,
                    "expected_future_use": spec.future_use,
                    "confidence": spec.confidence,
                    "salience": spec.salience,
                    "tags": list(spec.tags) + ["codex-test", DATASET_VERSION],
                    "metadata": {
                        "codex_test_dataset_version": DATASET_VERSION,
                        "codex_test_key": spec.key,
                        "codex_test_lane": spec.lane,
                    },
                },
            },
        )
        if response.status_code != 200:
            failed.append({"key": spec.key, "http_status": response.status_code})
            continue
        payload = response.json()
        result = payload.get("result", {})
        if not payload.get("ok"):
            failed.append({"key": spec.key, "error": payload.get("error")})
            continue
        keys[spec.key] = result.get("memory_id")
        if result.get("stored") is True:
            created += 1
        elif result.get("policy_decision") == "deduplicated":
            deduplicated += 1
    return {
        "requested": len(dataset),
        "created": created,
        "deduplicated": deduplicated,
        "failed": failed[:20],
        "failed_count": len(failed),
        "keys": keys,
    }


def _write_lifecycle_pair(
    client: TestClient,
    *,
    session_ids: dict[str, str],
) -> dict[str, Any]:
    old = _write_single_memory(
        client,
        session_id=session_ids["user"],
        spec=MemorySpec(
            key="ct_lifecycle_report_old",
            memory_type="user_preference",
            scope="user",
            content=(
                "Old Codex test report preference: evening audit reports should "
                "use two sections, Evidenze and Debolezze."
            ),
            reason="Old controlled preference that should be superseded.",
            future_use="Historical lifecycle test only.",
            tags=("report-format", "old", "lifecycle"),
            salience=0.6,
            lane="user",
        ),
    )
    new = _write_single_memory(
        client,
        session_id=session_ids["user"],
        spec=MemorySpec(
            key="ct_lifecycle_report_current",
            memory_type="user_preference",
            scope="user",
            content=(
                "Current Codex test report preference: evening audit reports "
                "should use three sections, Coerenza, Evidenze, Debolezze."
            ),
            reason="Current controlled preference replacing the old two-section version.",
            future_use="Use when evaluating evening audit report format.",
            tags=("report-format", "current", "lifecycle"),
            salience=0.86,
            lane="user",
        ),
    )
    supersede = client.post(
        "/mind/call",
        json={
            "session_id": session_ids["user"],
            "method": "POST",
            "path": "/mind/memory/supersede",
            "intent": "Codex lifecycle test: deprecate old report format.",
            "body": {
                "old_memory_id": old.get("memory_id"),
                "new_memory_id": new.get("memory_id"),
                "reason": "Current three-section report format supersedes old two-section format.",
                "deprecate_old": True,
            },
        },
    )
    return {
        "old": old,
        "new": new,
        "supersede": supersede.json() if supersede.status_code == 200 else {},
    }


def _write_single_memory(
    client: TestClient,
    *,
    session_id: str,
    spec: MemorySpec,
) -> dict[str, Any]:
    response = client.post(
        "/mind/call",
        json={
            "session_id": session_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "intent": f"Codex test lifecycle write for {spec.key}.",
            "body": {
                "type": spec.memory_type,
                "scope": spec.scope,
                "content": spec.content,
                "reason_for_storage": spec.reason,
                "expected_future_use": spec.future_use,
                "confidence": spec.confidence,
                "salience": spec.salience,
                "tags": list(spec.tags) + ["codex-test", DATASET_VERSION],
                "metadata": {
                    "codex_test_dataset_version": DATASET_VERSION,
                    "codex_test_key": spec.key,
                    "codex_test_lane": spec.lane,
                },
            },
        },
    )
    payload = response.json()
    result = payload.get("result", {})
    return {
        "ok": payload.get("ok"),
        "stored": result.get("stored"),
        "memory_id": result.get("memory_id"),
        "error": payload.get("error"),
    }


def _eval_cases() -> list[EvalCase]:
    return [
        EvalCase(
            name="direct_chocolate_limit",
            query="quando parliamo di dessert al cioccolato e benessere cosa devo ricordare?",
            scope="user",
            expected_keys=("ct_food_chocolate_limit",),
            forbidden_keys=("ct_far_distractor_000",),
        ),
        EvalCase(
            name="associative_evening_beverage",
            query="bevanda serale calda senza caffeina per restare concentrato",
            scope="user",
            expected_keys=("ct_food_evening_no_caffeine", "ct_food_chocolate_limit"),
            forbidden_keys=("ct_food_distractor_000",),
        ),
        EvalCase(
            name="negative_music_cooking",
            query="playlist jazz notturna mentre cucino",
            scope="user",
            expected_keys=(),
            forbidden_keys=("ct_food_chocolate_limit", "ct_food_evening_no_caffeine"),
        ),
        EvalCase(
            name="brief_when_tired",
            query="sono stanco, dammi una risposta asciutta e senza preamboli",
            scope="user",
            expected_keys=("ct_comm_brief_when_tired",),
        ),
        EvalCase(
            name="metacognitive_effort_routing",
            query="evitare ragionamento eccessivo su una richiesta semplice come ciao",
            scope="project",
            expected_keys=("ct_meta_effort_routing_simple_requests",),
        ),
        EvalCase(
            name="api_schema_recovery",
            query="endpoint API Mind sconosciuto parametri errati schema errore retry",
            scope="project",
            expected_keys=(
                "ct_project_schema_first_unknown_endpoint",
                "ct_meta_schema_error_recovery",
            ),
        ),
        EvalCase(
            name="episodic_bridge",
            query="memoria come ancora e recupero sessione sorgente per contesto storico",
            scope="project",
            expected_keys=("ct_project_memory_to_session_bridge",),
        ),
        EvalCase(
            name="privacy_profile_settings",
            query="profilo utente privacy fuso orario locale runtime context",
            scope="project",
            expected_keys=("ct_privacy_profile_scope",),
        ),
        EvalCase(
            name="lifecycle_current_report",
            query="report serale formato Coerenza Evidenze Debolezze",
            scope="user",
            expected_keys=("ct_lifecycle_report_current",),
            forbidden_keys=("ct_lifecycle_report_old",),
        ),
    ]


def _context_eval_cases() -> list[ContextEvalCase]:
    return [
        ContextEvalCase(
            name="context_evening_beverage",
            user_message=(
                "Vorrei una bevanda serale calda senza caffeina; considera quello "
                "che sai sulle mie preferenze personali."
            ),
            expected_keys=(
                "ct_food_evening_no_caffeine",
                "ct_food_chocolate_limit",
            ),
            expected_content_terms=("caffeina", "cioccolato"),
            forbidden_content_terms=("playlist", "basilico"),
            expected_behavior=(
                "Scarlet dovrebbe proporre una bevanda serale senza caffeina e "
                "tenere sullo sfondo il limite sul cioccolato, senza trasformarlo "
                "in tema principale se non serve."
            ),
        ),
        ContextEvalCase(
            name="context_brief_when_tired",
            user_message=(
                "Sono stanco, fammi una risposta asciutta e senza preamboli: "
                "che cosa dovrei tenere a mente adesso?"
            ),
            expected_keys=("ct_comm_brief_when_tired",),
            expected_content_terms=("stanco", "asciutte"),
            forbidden_content_terms=("weekend piovosi",),
            expected_behavior=(
                "Scarlet dovrebbe ridurre il volume, evitare preamboli e usare la "
                "memoria di stile come vincolo comunicativo."
            ),
        ),
        ContextEvalCase(
            name="context_semantic_to_episodic_bridge",
            user_message=(
                "Quando una memoria e solo un'ancora, come recuperi la sessione "
                "sorgente per verificare il contesto storico?"
            ),
            expected_keys=("ct_project_memory_to_session_bridge",),
            expected_content_terms=("source_session_id", "sessione episodica"),
            forbidden_content_terms=("salsa piccante",),
            expected_behavior=(
                "Scarlet dovrebbe riconoscere che la memoria semantica non basta "
                "come prova completa e che, se serve precisione, deve aprire la "
                "sessione di provenienza tramite source_session_id."
            ),
        ),
        ContextEvalCase(
            name="context_metacognitive_effort_routing",
            user_message=(
                "Se ti scrivo solo ciao o ti chiedo una conferma semplice, come "
                "decidi se evitare un ragionamento enorme?"
            ),
            expected_keys=("ct_meta_effort_routing_simple_requests",),
            expected_content_terms=("richiesta", "multi-step"),
            forbidden_content_terms=("fragole",),
            expected_behavior=(
                "Scarlet dovrebbe parlare di classificazione del livello della "
                "richiesta e proporzionalita dello sforzo, non di memoria utente."
            ),
        ),
        ContextEvalCase(
            name="context_negative_music_cooking",
            user_message=(
                "Mi consigli una playlist jazz notturna mentre cucino qualcosa "
                "di semplice?"
            ),
            expected_keys=(),
            expected_content_terms=(),
            forbidden_content_terms=("cioccolato", "caffeina", "source_session_id"),
            max_selected_count=0,
            expected_behavior=(
                "Scarlet non dovrebbe ricevere memorie personali forti su "
                "cioccolato/caffeina ne memorie progettuali: puo rispondere dal "
                "contesto corrente."
            ),
        ),
    ]


def _run_context_eval_cases(
    client: TestClient,
    cases: list[ContextEvalCase],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    passed = 0
    for case in cases:
        session = client.post(
            "/api/chat/sessions",
            json={"title": f"Codex Test Context Eval - {case.name}"},
        ).json()
        with client.stream(
            "POST",
            f"/api/chat/sessions/{session['id']}/turn/stream",
            json={"message": case.user_message, "max_tokens": 64},
        ) as response:
            events = [
                json.loads(line)
                for line in response.iter_lines()
                if line
            ]
        memory_context = _event_data(events, "memory_context")
        runtime_context = _event_data(events, "runtime_context")
        selected = memory_context.get("selected", [])
        near_miss = memory_context.get("near_miss", [])
        selected_text = _combined_memory_text(selected)
        selected_keys = tuple(
            key for key in (_memory_key(item) for item in selected) if key
        )
        expected_keys_present = {
            key: _memory_position_by_key(selected).get(key)
            for key in case.expected_keys
            if key in _memory_position_by_key(selected)
        }
        missing_keys = [
            key for key in case.expected_keys if key not in expected_keys_present
        ]
        missing_terms = [
            term
            for term in case.expected_content_terms
            if term.casefold() not in selected_text
        ]
        forbidden_present = [
            term
            for term in case.forbidden_content_terms
            if term.casefold() in selected_text
        ]
        selected_count = memory_context.get("selected_count")
        selected_count_violation = (
            case.max_selected_count is not None
            and isinstance(selected_count, int)
            and selected_count > case.max_selected_count
        )
        case_passed = (
            not missing_keys
            and not missing_terms
            and not forbidden_present
            and not selected_count_violation
        )
        if case_passed:
            passed += 1
        results.append(
            {
                "name": case.name,
                "passed": case_passed,
                "session_id": session["id"],
                "user_message": case.user_message,
                "expected_behavior": case.expected_behavior,
                "selected_count": memory_context.get("selected_count"),
                "candidate_count": memory_context.get("candidate_count"),
                "selected_keys": selected_keys,
                "missing_keys": missing_keys,
                "missing_terms": missing_terms,
                "forbidden_present": forbidden_present,
                "max_selected_count": case.max_selected_count,
                "selected_count_violation": selected_count_violation,
                "runtime_blocks": [
                    block.get("type")
                    for block in runtime_context.get("blocks", [])
                    if isinstance(block, dict)
                ],
                "selected": [
                    {
                        "rank": index + 1,
                        "id": item.get("id"),
                        "key": _memory_key(item),
                        "type": item.get("type"),
                        "scope": item.get("scope"),
                        "score": item.get("score"),
                        "content": item.get("content"),
                        "source_session_id": item.get("source_session_id"),
                        "why": item.get("why_relevant"),
                    }
                    for index, item in enumerate(selected)
                ],
                "near_miss": [
                    {
                        "rank": index + 1,
                        "id": item.get("id"),
                        "key": _memory_key(item),
                        "type": item.get("type"),
                        "scope": item.get("scope"),
                        "score": item.get("score"),
                    }
                    for index, item in enumerate(near_miss[:5])
                ],
            }
        )
    return {
        "passed": passed,
        "total": len(cases),
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "cases": results,
    }


def _event_data(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in events:
        if event.get("type") == event_type:
            data = event.get("data")
            return data if isinstance(data, dict) else {}
    return {}


def _combined_memory_text(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        for key in ("content", "reason_for_storage", "expected_future_use"):
            value = item.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts).casefold()


def _memory_position_by_key(memories: list[dict[str, Any]]) -> dict[str, int]:
    return {
        key: index
        for index, memory in enumerate(memories, start=1)
        if (key := _memory_key(memory))
    }


def _run_eval_cases(client: TestClient, cases: list[EvalCase]) -> dict[str, Any]:
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Codex Test Eval - memory retrieval"},
    ).json()
    results: list[dict[str, Any]] = []
    passed = 0
    for case in cases:
        response = client.post(
            "/mind/call",
            json={
                "session_id": session["id"],
                "method": "POST",
                "path": "/mind/memory/search",
                "intent": f"Codex eval search: {case.name}",
                "body": {
                    "query": case.query,
                    "scope": case.scope,
                    "top_k": case.top_k,
                    "include_low_confidence": True,
                },
            },
        )
        payload = response.json()
        memories = payload.get("result", {}).get("memories", [])
        key_positions = _key_positions(memories)
        expected_present = {
            key: key_positions.get(key)
            for key in case.expected_keys
            if key in key_positions
        }
        missing = [key for key in case.expected_keys if key not in key_positions]
        forbidden_present = {
            key: key_positions.get(key)
            for key in case.forbidden_keys
            if key in key_positions
        }
        case_passed = not missing and not forbidden_present
        if case_passed:
            passed += 1
        results.append(
            {
                "name": case.name,
                "passed": case_passed,
                "query": case.query,
                "scope": case.scope,
                "expected_present": expected_present,
                "missing": missing,
                "forbidden_present": forbidden_present,
                "returned": [
                    {
                        "rank": index + 1,
                        "id": memory.get("id"),
                        "key": _memory_key(memory),
                        "type": memory.get("type"),
                        "scope": memory.get("scope"),
                        "score": memory.get("score"),
                        "why": memory.get("why_relevant"),
                        "routes": _routes(memory),
                    }
                    for index, memory in enumerate(memories)
                ],
                "retrieval_shadow_status": payload.get("result", {})
                .get("retrieval_shadow", {})
                .get("status"),
                "retrieval_hybrid_mode": payload.get("result", {})
                .get("retrieval_hybrid", {})
                .get("mode"),
            }
        )
    return {
        "passed": passed,
        "total": len(cases),
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "cases": results,
    }


def _key_positions(memories: list[dict[str, Any]]) -> dict[str, int]:
    positions: dict[str, int] = {}
    for index, memory in enumerate(memories, start=1):
        key = _memory_key(memory)
        if key:
            positions[key] = index
    return positions


def _memory_key(memory: dict[str, Any]) -> str | None:
    metadata = memory.get("metadata")
    if isinstance(metadata, dict):
        key = metadata.get("codex_test_key")
        if isinstance(key, str):
            return key
    return None


def _routes(memory: dict[str, Any]) -> list[str]:
    signals = memory.get("retrieval_signals")
    if not isinstance(signals, dict):
        return []
    routes: list[str] = []
    if signals.get("graph"):
        routes.append("graph")
    hybrid = signals.get("hybrid")
    if isinstance(hybrid, dict):
        route = hybrid.get("route")
        if isinstance(route, str):
            routes.append(route)
    return routes


def _count_state(engine: Engine) -> dict[str, int]:
    with Session(engine) as db:
        return {
            "sessions": len(db.exec(select(ChatSession)).all()),
            "session_summaries": len(db.exec(select(SessionSummary)).all()),
            "memories_total": len(db.exec(select(MemoryRecord)).all()),
            "memories_active": len(
                db.exec(
                    select(MemoryRecord).where(MemoryRecord.status == "active")
                ).all()
            ),
            "codex_memories": len(
                [
                    memory
                    for memory in db.exec(select(MemoryRecord)).all()
                    if memory.metadata_json.get("codex_test_dataset_version")
                    == DATASET_VERSION
                ]
            ),
            "surfaces": len(db.exec(select(MemorySurface)).all()),
            "embedding_vectors": len(db.exec(select(EmbeddingVector)).all()),
            "graph_nodes": len(db.exec(select(MemoryGraphNode)).all()),
            "graph_edges": len(db.exec(select(MemoryGraphEdge)).all()),
        }


def _write_report(report: dict[str, Any]) -> None:
    root = Path(__file__).resolve().parents[2]
    run_dir = root / "app" / "evals" / "runs" / (
        datetime.now(UTC).strftime("%Y%m%d_%H%M%S_codex_test_memory")
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    summary_lines = [
        "# Codex Test Memory Evaluation",
        "",
        f"Dataset version: `{DATASET_VERSION}`",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], ensure_ascii=True, indent=2),
        "```",
        "",
        "## Eval",
        "",
        f"Passed: {report['eval']['passed']}/{report['eval']['total']}",
        "",
    ]
    for case in report["eval"]["cases"]:
        summary_lines.extend(
            [
                f"### {case['name']}",
                "",
                f"- Passed: `{case['passed']}`",
                f"- Missing: `{case['missing']}`",
                f"- Forbidden present: `{case['forbidden_present']}`",
                f"- Shadow status: `{case['retrieval_shadow_status']}`",
                f"- Hybrid mode: `{case['retrieval_hybrid_mode']}`",
                "",
            ]
        )
    summary_lines.extend(
        [
            "## Context Eval",
            "",
            f"Passed: {report['context_eval']['passed']}/{report['context_eval']['total']}",
            "",
        ]
    )
    for case in report["context_eval"]["cases"]:
        summary_lines.extend(
            [
                f"### {case['name']}",
                "",
                f"- Passed: `{case['passed']}`",
                f"- Selected keys: `{case['selected_keys']}`",
                f"- Missing keys: `{case['missing_keys']}`",
                f"- Missing terms: `{case['missing_terms']}`",
                f"- Forbidden present: `{case['forbidden_present']}`",
                f"- Selected count violation: `{case['selected_count_violation']}`",
                f"- Expected behavior: {case['expected_behavior']}",
                "",
            ]
        )
    (run_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
