from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

import networkx as nx
from sqlmodel import Session

from app.mind.facts import fact_search_text
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord


GRAPH_RETRIEVAL_POLICY = "networkx_associative_memory_graph_v1"

_WORD_RE = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)
_LOW_SIGNAL_TOKENS = {
    "a",
    "ad",
    "al",
    "alla",
    "allo",
    "anche",
    "che",
    "con",
    "da",
    "de",
    "dei",
    "del",
    "della",
    "di",
    "e",
    "il",
    "in",
    "io",
    "la",
    "le",
    "lo",
    "ma",
    "mi",
    "ne",
    "nel",
    "non",
    "o",
    "per",
    "poi",
    "se",
    "sono",
    "su",
    "the",
    "to",
    "and",
    "or",
    "of",
    "for",
    "in",
    "with",
}


@dataclass(frozen=True)
class GraphMemorySignal:
    memory_id: str
    score: float
    why_relevant: str
    domains: list[str]
    paths: list[dict[str, Any]]


def build_memory_graph_expansion(
    db: Session,
    *,
    query: str,
    memories: list[MemoryRecord],
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
    max_hops: int = 2,
    limit: int = 20,
) -> dict[str, Any]:
    facts_by_memory = facts_by_memory or {}
    payload: dict[str, Any] = {
        "operation": "memory.graph_expansion",
        "ok": True,
        "status": "completed",
        "backend": "networkx",
        "ranking_policy": GRAPH_RETRIEVAL_POLICY,
        "graph_policy": (
            "dynamic_graph_only: no hard-coded domain vocabulary; graph seeds "
            "come from stored memory/fact/session/type/scope/tag nodes"
        ),
        "query": query,
        "max_hops": max_hops,
        "candidate_memory_count": len(memories),
        "seed_nodes": [],
        "concept_matches": [],
        "domain_matches": [],
        "results": [],
        "graph_stats": {},
    }
    if not memories:
        payload.update({"status": "no_candidate_memories"})
        return payload

    memory_by_id = {memory.id: memory for memory in memories}
    graph = nx.Graph()
    _add_memory_nodes(
        graph,
        memories=memories,
        facts_by_memory=facts_by_memory,
    )
    _add_existing_graph_nodes_and_edges(db, graph, memory_by_id=memory_by_id)
    concept_matches = _add_domain_bridge_nodes(graph, memories)
    seed_nodes = _query_seed_nodes(graph, query=query)
    payload["concept_matches"] = concept_matches[:50]
    payload["domain_matches"] = concept_matches[:50]
    payload["seed_nodes"] = [
        {
            "node_id": node_id,
            "label": graph.nodes[node_id].get("label"),
            "node_type": graph.nodes[node_id].get("node_type"),
            "matched_terms": data.get("matched_terms", []),
            "seed_score": round(data.get("seed_score", 0.0), 4),
        }
        for node_id, data in seed_nodes
    ][:20]
    payload["graph_stats"] = {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "memory_node_count": len(memories),
        "concept_node_count": len(
            [
                node_id
                for node_id, node in graph.nodes(data=True)
                if str(node.get("node_type") or "").startswith("concept")
            ]
        ),
    }

    if not seed_nodes:
        payload["status"] = "no_query_seed"
        return payload

    signals = _score_memory_nodes(
        graph,
        seed_nodes=seed_nodes,
        memory_by_id=memory_by_id,
        max_hops=max_hops,
        limit=limit,
    )
    payload["results"] = [
        {
            "memory_id": signal.memory_id,
            "score": round(signal.score, 6),
            "why_relevant": signal.why_relevant,
            "domains": signal.domains,
            "paths": signal.paths[:5],
        }
        for signal in signals
    ]
    if not signals:
        payload["status"] = "no_memory_expansion"
    return payload


def graph_signals_by_memory(payload: dict[str, Any] | None) -> dict[str, GraphMemorySignal]:
    if not isinstance(payload, dict):
        return {}
    results = payload.get("results")
    if not isinstance(results, list):
        return {}
    signals: dict[str, GraphMemorySignal] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        memory_id = item.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id:
            continue
        signals[memory_id] = GraphMemorySignal(
            memory_id=memory_id,
            score=float(item.get("score") or 0.0),
            why_relevant=str(item.get("why_relevant") or ""),
            domains=[
                str(domain)
                for domain in item.get("domains", [])
                if isinstance(domain, str)
            ],
            paths=[
                path
                for path in item.get("paths", [])
                if isinstance(path, dict)
            ],
        )
    return signals


def _add_memory_nodes(
    graph: nx.Graph,
    *,
    memories: Iterable[MemoryRecord],
    facts_by_memory: dict[str, list[MemoryFact]],
) -> None:
    for memory in memories:
        node_id = _memory_node_id(memory.id)
        graph.add_node(
            node_id,
            node_type="memory",
            label=memory.content,
            scope=memory.scope,
            memory_id=memory.id,
            text=_memory_text(memory, facts=facts_by_memory.get(memory.id, [])),
            concepts=[],
        )


def _add_existing_graph_nodes_and_edges(
    db: Session,
    graph: nx.Graph,
    *,
    memory_by_id: dict[str, MemoryRecord],
) -> None:
    nodes = repositories.list_memory_graph_nodes(
        db,
        limit=max(len(memory_by_id) * 8, 100),
    )
    allowed_node_ids: set[str] = set(graph.nodes)
    for node in nodes:
        if node.source_memory_id and node.source_memory_id not in memory_by_id:
            continue
        node_id = f"stored:{node.id}"
        allowed_node_ids.add(node_id)
        graph.add_node(
            node_id,
            node_type=f"stored_{node.node_type}",
            label=node.label,
            scope=node.scope,
            memory_id=node.source_memory_id,
            text=" ".join([node.label, " ".join(node.aliases_json)]),
            concepts=[],
        )
        if node.source_memory_id in memory_by_id:
            graph.add_edge(
                node_id,
                _memory_node_id(node.source_memory_id),
                relation="stored_graph_evidence",
                weight=0.65,
            )

    edges = repositories.list_memory_graph_edges(
        db,
        limit=max(len(memory_by_id) * 12, 100),
    )
    for edge in edges:
        source_id = f"stored:{edge.source_node_id}"
        target_id = f"stored:{edge.target_node_id}"
        if source_id not in allowed_node_ids or target_id not in allowed_node_ids:
            continue
        graph.add_edge(
            source_id,
            target_id,
            relation=edge.relation,
            weight=_relation_weight(edge.relation),
        )


def _add_domain_bridge_nodes(
    graph: nx.Graph,
    memories: list[MemoryRecord],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for memory in memories:
        for concept_type, label in _memory_concepts(memory):
            concept_id = _concept_node_id(concept_type, label)
            concept_label = label.replace("_", " ")
            graph.add_node(
                concept_id,
                node_type=f"concept_{concept_type}",
                label=concept_label,
                text=concept_label,
                concept=f"{concept_type}:{label}",
                concepts=[f"{concept_type}:{label}"],
            )
            memory_node_id = _memory_node_id(memory.id)
            graph.nodes[memory_node_id].setdefault("concepts", []).append(
                f"{concept_type}:{label}"
            )
            graph.add_edge(
                concept_id,
                memory_node_id,
                relation=f"shares_{concept_type}",
                weight=0.8,
            )
            matches.append(
                {
                    "memory_id": memory.id,
                    "concept": f"{concept_type}:{label}",
                    "matched_terms": _tokens(label.replace("_", " "))[:8],
                }
            )
    return matches


def _query_seed_nodes(
    graph: nx.Graph,
    *,
    query: str,
) -> list[tuple[str, dict[str, Any]]]:
    query_text = _normalize(query)
    query_tokens = set(_tokens(query))
    seeds: list[tuple[str, dict[str, Any]]] = []
    for node_id, node in graph.nodes(data=True):
        text = _normalize(str(node.get("text") or node.get("label") or ""))
        matched_terms = _matched_query_terms(
            query_text=query_text,
            query_tokens=query_tokens,
            target_text=text,
        )
        if not matched_terms:
            continue
        seed_score = len(matched_terms)
        if str(node.get("node_type") or "").startswith("concept"):
            seed_score += 0.75
        if node.get("node_type") == "memory":
            seed_score += 1.0
        seeds.append(
            (
                node_id,
                {
                    "matched_terms": matched_terms[:8],
                    "seed_score": seed_score,
                },
            )
        )
    seeds.sort(key=lambda item: item[1]["seed_score"], reverse=True)
    return seeds[:8]


def _score_memory_nodes(
    graph: nx.Graph,
    *,
    seed_nodes: list[tuple[str, dict[str, Any]]],
    memory_by_id: dict[str, MemoryRecord],
    max_hops: int,
    limit: int,
) -> list[GraphMemorySignal]:
    scores: dict[str, float] = {}
    paths: dict[str, list[dict[str, Any]]] = {}
    domains_by_memory: dict[str, set[str]] = {}

    for seed_id, seed_data in seed_nodes:
        if graph.nodes[seed_id].get("node_type") == "memory":
            memory_id = graph.nodes[seed_id].get("memory_id")
            if memory_id in memory_by_id:
                seed_score = float(seed_data.get("seed_score") or 1.0)
                scores[memory_id] = scores.get(memory_id, 0.0) + seed_score
                concepts = [
                    str(item)
                    for item in graph.nodes[seed_id].get("concepts", [])
                    if isinstance(item, str)
                ]
                domains_by_memory.setdefault(memory_id, set()).update(concepts)
                paths.setdefault(memory_id, []).append(
                    {
                        "seed": graph.nodes[seed_id].get("label"),
                        "seed_type": graph.nodes[seed_id].get("node_type"),
                        "hops": 0,
                        "matched_terms": seed_data.get("matched_terms", []),
                        "relations": [],
                        "score_contribution": round(seed_score, 6),
                    }
                )
        lengths = nx.single_source_shortest_path_length(
            graph,
            seed_id,
            cutoff=max_hops,
        )
        for node_id, hops in lengths.items():
            if hops <= 0 or graph.nodes[node_id].get("node_type") != "memory":
                continue
            memory_id = graph.nodes[node_id].get("memory_id")
            if memory_id not in memory_by_id:
                continue
            memory = memory_by_id[memory_id]
            path = nx.shortest_path(graph, seed_id, node_id)
            path_weight = _path_weight(graph, path)
            seed_score = float(seed_data.get("seed_score") or 1.0)
            contribution = (
                seed_score
                * path_weight
                * (1.0 / max(hops, 1))
            )
            scores[memory_id] = scores.get(memory_id, 0.0) + contribution
            domains = [
                str(graph.nodes[path_node].get("concept"))
                for path_node in path
                if graph.nodes[path_node].get("concept")
            ]
            domains_by_memory.setdefault(memory_id, set()).update(domains)
            paths.setdefault(memory_id, []).append(
                {
                    "seed": graph.nodes[seed_id].get("label"),
                    "seed_type": graph.nodes[seed_id].get("node_type"),
                    "hops": hops,
                    "matched_terms": seed_data.get("matched_terms", []),
                    "relations": _path_relations(graph, path),
                    "score_contribution": round(contribution, 6),
                }
            )

    signals = [
        GraphMemorySignal(
            memory_id=memory_id,
            score=score,
            why_relevant=(
                "associative graph expansion: "
                + ", ".join(sorted(domains_by_memory.get(memory_id, set())))
            ),
            domains=sorted(domains_by_memory.get(memory_id, set())),
            paths=paths.get(memory_id, []),
        )
        for memory_id, score in scores.items()
        if score > 0
    ]
    signals.sort(key=lambda item: item.score, reverse=True)
    return signals[:limit]


def _path_weight(graph: nx.Graph, path: list[str]) -> float:
    weight = 1.0
    for source, target in zip(path, path[1:]):
        edge = graph.get_edge_data(source, target) or {}
        weight *= float(edge.get("weight") or 0.5)
    return max(weight, 0.01)


def _path_relations(graph: nx.Graph, path: list[str]) -> list[str]:
    relations: list[str] = []
    for source, target in zip(path, path[1:]):
        edge = graph.get_edge_data(source, target) or {}
        relation = edge.get("relation")
        if isinstance(relation, str):
            relations.append(relation)
    return relations


def _memory_text(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
    return " ".join(
        item
        for item in [
            memory.content,
            memory.memory_type,
            memory.scope,
            " ".join(memory.tags_json),
            fact_search_text(facts),
        ]
        if item
    )


def _matched_query_terms(
    *,
    query_text: str,
    query_tokens: set[str],
    target_text: str,
) -> list[str]:
    target_tokens = set(_tokens(target_text))
    token_matches = sorted(query_tokens & target_tokens)
    phrase_matches = [
        token
        for token in query_tokens
        if len(token) >= 6 and token in target_text
    ]
    return sorted(set(token_matches + phrase_matches))


def _tokens(value: str) -> list[str]:
    return [
        token
        for token in (_normalize(match.group(0)) for match in _WORD_RE.finditer(value))
        if len(token) > 2 and token not in _LOW_SIGNAL_TOKENS
    ]


def _normalize(value: str) -> str:
    return value.casefold().replace("-", " ").replace("_", " ")


def _memory_node_id(memory_id: str) -> str:
    return f"memory:{memory_id}"


def _memory_concepts(memory: MemoryRecord) -> list[tuple[str, str]]:
    concepts = [
        ("type", memory.memory_type),
        ("scope", memory.scope),
    ]
    concepts.extend(("tag", tag) for tag in memory.tags_json[:12])
    normalized: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for concept_type, label in concepts:
        label = _normalize_label(label)
        if not label:
            continue
        key = (concept_type, label)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ_ -]+", " ", value.casefold())
    normalized = re.sub(r"[\s-]+", "_", normalized)
    return re.sub(r"_+", "_", normalized).strip("_")[:120]


def _concept_node_id(concept_type: str, label: str) -> str:
    return f"concept:{concept_type}:{label}"


def _relation_weight(relation: str) -> float:
    weights = {
        "has_fact": 0.9,
        "about_entity": 0.85,
        "evidenced_by_session": 0.65,
        "supersedes": 0.75,
        "superseded_by": 0.75,
        "supersedes_fact": 0.75,
        "superseded_by_fact": 0.75,
        "stored_graph_evidence": 0.65,
    }
    return weights.get(relation, 0.6)
