import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.runtime.preferences import RuntimePreferences
from app.storage.models import ChatSession, Message


METACOGNITIVE_CONTEXT_VERSION = "metacognitive-context-shadow-v1"


@dataclass(frozen=True)
class MetacognitiveLesson:
    id: str
    title: str
    lesson: str
    trigger_conditions: list[str]
    anti_conditions: list[str]
    recommended_action: str
    cost_impact: str
    risk_if_overused: str


LESSONS = {
    "simple_turn_effort_guard": MetacognitiveLesson(
        id="simple_turn_effort_guard",
        title="Calibra lo sforzo sulle richieste semplici",
        lesson=(
            "Quando la richiesta e' conversazionale o diretta, Scarlet deve "
            "rispondere in modo compatto senza trasformarla in investigazione."
        ),
        trigger_conditions=[
            "messaggio breve",
            "nessun richiamo esplicito a fonti, passato, memoria, stato o API",
            "nessuna decisione operativa o claim sensibile richiesto",
        ],
        anti_conditions=[
            "richiesta su dati storici o fonti",
            "richiesta di verifica",
            "conflitti o evidenze mancanti nel contesto",
        ],
        recommended_action=(
            "Risposta diretta; nessuna metacognizione/tool rituale se il "
            "contesto visibile basta."
        ),
        cost_impact="riduce token, latenza e overthinking",
        risk_if_overused=(
            "puo' far sottovalutare richieste brevi ma source-sensitive"
        ),
    ),
    "memory_commitment_guard": MetacognitiveLesson(
        id="memory_commitment_guard",
        title="Non promettere memoria senza azione",
        lesson=(
            "Se emerge un fatto durevole o Scarlet dice che lo ricordera', "
            "la promessa deve corrispondere a un salvataggio reale o a una "
            "risposta che evita la promessa."
        ),
        trigger_conditions=[
            "fatto personale, preferenza, vincolo o milestone potenzialmente durevole",
            "frasi come ricordalo, tienilo a mente, me lo ricordero'",
            "risposta prevista con impegno mnemonico",
        ],
        anti_conditions=[
            "battuta o flusso temporaneo",
            "informazione sensibile non necessaria o non pertinente",
            "fatto gia' presente e aggiornato in memoria",
        ],
        recommended_action=(
            "Verificare se serve memory.write; se non si salva, non dire che "
            "e' stato ricordato."
        ),
        cost_impact="riduce memorie mancate e promesse incoerenti",
        risk_if_overused="puo' creare memorie rumorose o troppo granulari",
    ),
    "historical_recall_evidence_guard": MetacognitiveLesson(
        id="historical_recall_evidence_guard",
        title="Apri evidenza quando la richiesta riguarda il passato",
        lesson=(
            "Quando l'utente chiede cosa e' successo, cosa si era deciso o "
            "cosa Scarlet ricorda, la risposta deve distinguere memoria "
            "semantica, sessione episodica e inferenza."
        ),
        trigger_conditions=[
            "richiesta su ieri, oggi, sessioni precedenti o cose gia' dette",
            "domande su decisioni, test, bug o sviluppi passati",
            "memoria selezionata che rimanda a una sessione sorgente",
        ],
        anti_conditions=[
            "utente chiede solo opinione o brainstorming nuovo",
            "stesso turno contiene gia' evidenza sufficiente",
        ],
        recommended_action=(
            "Usare memoria o session recall proporzionalmente; aprire la "
            "sessione sorgente quando serve un dato verificato."
        ),
        cost_impact="aumenta tool/latency solo quando la prova storica serve",
        risk_if_overused="puo' rallentare risposte dove basta il contesto corrente",
    ),
    "source_sensitive_claim_guard": MetacognitiveLesson(
        id="source_sensitive_claim_guard",
        title="Verifica i claim source-sensitive",
        lesson=(
            "Per stato del sistema, API, bug, versioni, implementazioni e "
            "decisioni progettuali, Scarlet deve basare la risposta su "
            "evidenze disponibili e nominare incertezza/residui."
        ),
        trigger_conditions=[
            "richiesta su implementato, stato, bug, versione, endpoint o comportamento reale",
            "parole come verifica, sicuro, conferma, evidenza, test",
            "claim che potrebbe guidare decisioni progettuali",
        ],
        anti_conditions=[
            "domanda casuale senza impatto operativo",
            "risposta gia' coperta da evidenza appena fornita dall'utente",
        ],
        recommended_action=(
            "Ispezionare evidenze/API Mind se necessario; evitare claim forti "
            "senza fonte."
        ),
        cost_impact="aumenta accuratezza a costo di tool/tempo proporzionali",
        risk_if_overused="puo' produrre verifiche ridondanti",
    ),
}


def build_metacognitive_context_payload(
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    history: list[Message],
    memory_context: dict[str, Any],
    timestamp: datetime,
    runtime_preferences: RuntimePreferences,
    mode: str = "shadow",
    max_lessons: int = 3,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    selected = _select_lessons(
        current_user_message=current_user_message,
        history=history,
        memory_context=memory_context,
        max_lessons=max_lessons,
    )
    return {
        "operation": "metacognitive.context",
        "schema_version": METACOGNITIVE_CONTEXT_VERSION,
        "mode": normalized_mode,
        "model_facing": normalized_mode == "inject",
        "generated_at": timestamp.astimezone(timezone.utc).isoformat(),
        "session_id": chat_session.id,
        "turn_id": turn_id,
        "source": "backend.shadow_metacognition",
        "policy": {
            "purpose": (
                "Shadow candidate lessons about Scarlet's own operating "
                "patterns. In shadow mode this block is observable only and "
                "must not influence the model request."
            ),
            "injection_policy": (
                "Only mode=inject may add this block to runtime_context.blocks "
                "for controlled A/B tests."
            ),
            "selection_policy": (
                "Prefer no lesson over noisy generic advice. Selected lessons "
                "must be few, trigger-matched, and testable."
            ),
        },
        "selection": {
            "selected_count": len(selected),
            "max_lessons": max_lessons,
            "negative_evidence": (
                "no_metacognitive_lesson_selected"
                if not selected
                else "selected_lessons_available"
            ),
        },
        "triggers": [item["trigger"] for item in selected],
        "lessons": [item["lesson"] for item in selected],
        "runtime_inputs": {
            "message_chars": len(current_user_message.content),
            "visible_history_messages": len(
                [message for message in history if message.role in {"user", "assistant"}]
            ),
            "memory_selected_count": memory_context.get("selected_count", 0),
            "memory_near_miss_count": len(memory_context.get("near_miss", [])),
            "runtime_language": runtime_preferences.language,
        },
    }


def metacognitive_context_runtime_block(
    metacognitive_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": "turn.metacognitive_context",
        "type": "metacognitive_context",
        "scope": "turn",
        "lifetime": "turn",
        "source": "backend.shadow_metacognition",
        "content": {
            "policy": metacognitive_context.get("policy", {}),
            "selection": metacognitive_context.get("selection", {}),
            "triggers": metacognitive_context.get("triggers", []),
            "lessons": metacognitive_context.get("lessons", []),
        },
    }


def _select_lessons(
    *,
    current_user_message: Message,
    history: list[Message],
    memory_context: dict[str, Any],
    max_lessons: int,
) -> list[dict[str, Any]]:
    text = current_user_message.content.strip()
    selected: list[dict[str, Any]] = []

    if _is_simple_direct_turn(text):
        selected.append(_selected_lesson("simple_turn_effort_guard", "simple_direct_turn", 0.78))

    if _has_memory_commitment_signal(text):
        selected.append(_selected_lesson("memory_commitment_guard", "memory_commitment_signal", 0.86))

    if _has_historical_recall_signal(text) or memory_context.get("selected_count", 0):
        selected.append(
            _selected_lesson(
                "historical_recall_evidence_guard",
                "historical_or_memory_evidence_signal",
                0.82,
            )
        )

    if _has_source_sensitive_signal(text, history):
        selected.append(
            _selected_lesson(
                "source_sensitive_claim_guard",
                "source_sensitive_claim_signal",
                0.84,
            )
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in selected:
        lesson_id = str(item["lesson"].get("id", ""))
        if lesson_id in seen:
            continue
        seen.add(lesson_id)
        deduped.append(item)
    return deduped[:max_lessons]


def _selected_lesson(
    lesson_id: str,
    trigger: str,
    confidence: float,
) -> dict[str, Any]:
    lesson = LESSONS[lesson_id]
    return {
        "trigger": {
            "id": trigger,
            "confidence": confidence,
        },
        "lesson": {
            "id": lesson.id,
            "title": lesson.title,
            "lesson": lesson.lesson,
            "trigger_conditions": lesson.trigger_conditions,
            "anti_conditions": lesson.anti_conditions,
            "recommended_action": lesson.recommended_action,
            "cost_impact": lesson.cost_impact,
            "risk_if_overused": lesson.risk_if_overused,
            "confidence": confidence,
        },
    }


def _is_simple_direct_turn(text: str) -> bool:
    words = _tokens(text)
    if len(words) > 12:
        return False
    return not (
        _has_memory_commitment_signal(text)
        or _has_historical_recall_signal(text)
        or _has_source_sensitive_signal(text, [])
    )


def _has_memory_commitment_signal(text: str) -> bool:
    lowered = text.lower()
    direct_patterns = [
        r"\bricord",
        r"\btieni(lo|la)? a mente\b",
        r"\bsegnati\b",
        r"\bpreferisc",
        r"\bmi piace\b",
        r"\bnon mi piace\b",
        r"\bsono allerg",
        r"\bmi da fastidio\b",
    ]
    return any(re.search(pattern, lowered) for pattern in direct_patterns)


def _has_historical_recall_signal(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        r"\bieri\b",
        r"\bsessioni? di oggi\b",
        r"\bchat di oggi\b",
        r"\bscorsa sessione\b",
        r"\bsessione precedente\b",
        r"\bavevamo\b",
        r"\babbiamo detto\b",
        r"\bdi cosa abbiamo parlato\b",
        r"\bti ricordi\b",
        r"\bstorico\b",
    ]
    return any(re.search(pattern, lowered) for pattern in patterns)


def _has_source_sensitive_signal(text: str, history: list[Message]) -> bool:
    lowered = text.lower()
    patterns = [
        r"\bverifica\b",
        r"\bconferma\b",
        r"\bsicura?\b",
        r"\bevidenz",
        r"\btest\b",
        r"\bbug\b",
        r"\bendpoint\b",
        r"\bimplementat",
        r"\bversione\b",
        r"\bstato (del sistema|del progetto|attuale)\b",
        r"\ba che punto\b",
        r"\bdove siamo arrivati\b",
        r"\bapi\b",
    ]
    if any(re.search(pattern, lowered) for pattern in patterns):
        return True
    visible_history = [message for message in history if message.role in {"user", "assistant"}]
    return len(visible_history) > 20 and "riassum" in lowered


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower())


def _normalize_mode(mode: str) -> str:
    lowered = mode.strip().lower()
    if lowered in {"off", "shadow", "inject"}:
        return lowered
    return "shadow"
