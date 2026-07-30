# Mappa Tecnica

Ultima verifica: 2026-07-31
Baseline backend: V1.68.0
Stato: mappa developer canonica delle scelte tecniche correnti

Questo documento dice quale tecnologia o soluzione custom esiste, quale
problema risolve e con quale stato. Non sostituisce i contratti di dominio ne'
un inventario di dipendenze transitive. Una libreria installata non e' una
capacita' attiva: il codice e l'evidenza runtime restano l'autorita'.

## Come Leggerla

- **Attiva**: percorso supportato nel runtime corrente.
- **Attiva su configurazione**: implementata e usata soltanto quando la
  configurazione dell'ambiente la abilita.
- **Sperimentale**: superficie limitata di ricerca o adattamento, non
  autorita' del Core.
- **Shadow**: osserva o confronta, senza decidere la cognizione ordinaria.

## Piattaforma E Persistenza

| Tecnologia / soluzione | Stato e uso | Motivo della scelta | Fonte tecnica |
|---|---|---|---|
| Python, FastAPI, Uvicorn | Attiva. Backend HTTP, worker e OpenAPI. | Runtime tipizzato e leggero per API, streaming e processi di sfondo. | `backend/app/main.py`, `backend/pyproject.toml` |
| Pydantic Settings | Attiva. Configurazione tipizzata da ambiente. | Distingue provider, database, limiti e modalita' senza configurazione implicita. | `backend/app/config.py` |
| SQLModel + SQLite | Attiva. Archivio canonico di sessioni, messaggi, memorie, tracce, eventi, attivazioni e artefatti derivati. Non usiamo PostgreSQL oggi. | Un solo database transazionale e ispezionabile; ruoli produzione/laboratorio/test impediscono di trattare copie o dati reali come equivalenti. | [Database topology](database-topology.md), `backend/app/storage/` |
| SQLite FTS5 | Attiva. Ricerca sparsa/lessicale sui documenti di memoria. | Recupero locale, trasparente e riproducibile come fonte candidata, non giudizio semantico finale. | `backend/app/storage/db.py`, `backend/app/mind/search.py` |
| Grafo memoria SQL + NetworkX | Attiva. Nodi e archi canonici sono in SQLite; NetworkX costruisce l'espansione associativa in processo. | Permette relazioni e provenienza senza un secondo database-grafo autoritativo. | `backend/app/storage/models.py`, `backend/app/mind/graph_retrieval.py` |
| Docker | Attiva in VPS. Contenitore backend; il database di produzione resta un mount separato. | Rilasci ripetibili senza trasferire DB o segreti con il codice. | `backend/Dockerfile`, [Release process](release-process.md) |

## Modelli E Retrieval

| Tecnologia / soluzione | Stato e uso | Motivo della scelta | Fonte tecnica |
|---|---|---|---|
| MiniMax M3 | Attiva. Modello nativo di Scarlet nei turni umani e autonomi. | Un solo modello agente detiene risposta, tool use, episodi e decisioni cognitive. | `backend/app/config.py`, `backend/app/llm/minimax_client.py`, [Core runtime](core-runtime-contract.md) |
| MiniMax M2.7 | Attiva come profilo ausiliario, mai come Scarlet. | Svolge proposte strutturate e verifiche semantiche preparatorie senza sostituire la decisione del modello agente. | `backend/app/llm/factory.py`, `backend/app/runtime/endogenous_cognition.py` |
| Anthropic-compatible provider port | Attiva. Il client `anthropic` trasporta MiniMax e l'adapter Qwen. | Separa il ciclo nativo da un fornitore e conserva stop reason, tool e streaming. | `backend/app/llm/provider.py`, `backend/app/llm/minimax_client.py` |
| Qwen | Sperimentale/alternativo. Adapter configurabile, fuori dal percorso normale di Scarlet. | Mantiene una via provider alternativa senza deformare il contratto nativo MiniMax. | `backend/app/llm/qwen_client.py` |
| OpenRouter embeddings + rerank | Attiva su configurazione. In produzione e' abilitato per candidati densi e rerank finale delle memorie; i default del codice restano disattivi senza credenziali. | Embedding semantici e rerank LLM migliorano il recupero senza rendere punteggi manuali l'autorita' finale. | `backend/app/mind/openrouter_retrieval.py`, `backend/app/mind/relevance_rerank.py`, [Memory branch](branches/memory.md) |
| `embedding_vectors` SQLite | Attiva quando il retrieval denso e' configurato. Cache persistente di embedding per `memory_surfaces`, con confronto limitato in processo. **Non e' un indice ANN vettoriale.** | Evita rigenerazioni e conserva la provenienza senza creare un secondo archivio canonico. | `backend/app/storage/models.py`, `backend/app/mind/shadow_retrieval.py` |
| Milvus Lite | Shadow. Opzionale e rebuildable; usa l'embedding hash locale non semantico e non decide il ranking ordinario. **Non e' il motore vettoriale attivo.** | Verifica la meccanica di indicizzazione/ricerca e mantiene una futura opzione ANN, senza dichiarare una falsa capacita' semantica. | `backend/app/mind/shadow_retrieval.py`, [Database topology](database-topology.md) |

Un vettore e' una rappresentazione numerica usata per proporre elementi
semanticamente vicini. Un indice vettoriale ANN serve a cercare rapidamente
fra moltissimi vettori. Oggi Scarlet usa FTS5, grafo e candidati densi
configurati; non usa un indice ANN come autorita' del retrieval. Un'eventuale
adozione futura di Milvus o equivalente dovra' sostituire solo il lookup dei
candidati densi: SQLite, provenienza e rerank restano i confini da preservare.

## Soluzioni Custom Del Core

| Soluzione | Stato e uso | Motivo della scelta | Fonte tecnica |
|---|---|---|---|
| Kernel di turno condiviso | Attiva. Unisce il ciclo nativo umano e autonomo dopo il confine di ingresso della sorgente. | Evita due implementazioni divergenti di contesto, strumenti, persistenza, finalita' e compattazione. | `backend/app/runtime/turn_kernel.py`, [Core runtime](core-runtime-contract.md) |
| Compilatore del contesto dinamico | Attiva. Produce `scarlet-model-context-v2` e accounting per entrambi i cicli. | Il modello riceve un contratto compatto e ordinato; prove ricche, diagnostica e UI restano fuori dal prompt. | `backend/app/mind/context_projection.py`, `backend/app/runtime/context_accounting.py` |
| `mind_shell(command, intent)` | Attiva. Unica superficie cognitiva esposta al modello. | Mantiene piccoli, navigabili e tracciabili i comandi degli organi. | `backend/app/mind/command_registry.py`, `backend/app/runtime/mind_tool_runner.py` |
| Memorie, superfici, provenienza e KG | Attiva. Memorie atomiche e fonti restano in SQLite; superfici e grafo sono indici/derivati navigabili. | Separa il dato canonico dai modi di recuperarlo e non sostituisce l'origine con una sintesi. | `backend/app/mind/memory_read.py`, `backend/app/mind/memory_write.py`, `backend/app/storage/models.py` |
| Compattazione `C/H/A` | Attiva. Riassunto, coda cronologica integra e spazio attivo sono artefatti derivati; la storia canonica non viene cancellata. | Mantiene una finestra operativa sostenibile senza perdere navigabilita' e provenienza. | `backend/app/runtime/history_runtime.py`, `backend/app/runtime/history_compaction.py`, `backend/app/runtime/context_accounting.py` |
| Tracce, eventi e Stream V2 | Attiva. Eventi persistenti e riprendibili alimentano debug e Product UI. | Rende un turno ispezionabile e la UI un consumatore dei fatti del Core. | `backend/app/api/chat_stream_v2.py`, [Stream V2](stream-v2-contract.md) |
| Research Lab Python/SymPy + web | Distribuito sulla VPS protetta in V1.66.0, abilitato solo da ambiente operatore e disabilitato altrove per default. `lab` conserva ricevute esplicite; Python gira solo in sidecar senza rete e il web passa da lettura HTTPS limitata. | Aggiunge calcolo e fonti esterne senza eseguire codice nel backend, senza accesso a DB/segreti e senza iniezione automatica nella cognizione. | [Research Lab](research-lab.md), `docker-compose.research-lab.yml`, `backend/app/research_lab/`, `backend/research_lab_runner/` |
| Manutenzione e autonomia | Attiva. Worker, scheduler, Workspace, episodi e finestre endogenee usano evidenza canonica; M2.7 propone, M3 Scarlet decide. | Distingue meccanica deterministica e giudizio semantico senza una seconda cognizione parallela. | `backend/app/runtime/maintenance.py`, `autonomy.py`, `cognitive_workspace.py`, `endogenous_cognition.py` |
| Famiglie di contesto e perception inbox | Sperimentale, con ammissione limitata. Classifica fonti e conserva osservazioni prima di un uso cognitivo esteso. | Prepara device, segnali e futuro embodiment senza iniettare rumore direttamente nel contesto agente. | `backend/app/mind/context_families.py`, `backend/app/runtime/device_perception_adapter.py` |

## Client, Adattatori E Moduli

| Tecnologia / soluzione | Stato e uso | Motivo della scelta | Fonte tecnica |
|---|---|---|---|
| React, TypeScript, Vite, Tailwind | Attiva. Product UI web e base condivisa dell'app. | Client moderno e tipizzato che consuma gli stessi contratti HTTP/eventi del Core. | `frontend/package.json`, [Product UI](product-ui-prototype.md) |
| Motion, GSAP, Lucide | Attiva nella UI. Movimento, transizioni e icone. | Esprimono eventi e stato senza assegnare cognizione al client. | `frontend/package.json`, `frontend/src/` |
| Capacitor Android | Attiva. Confeziona la stessa UI e ospita il laboratorio device. | Evita due prodotti con logiche diverse e permette osservazioni native controllate. | `frontend/capacitor.config.ts`, `frontend/src/deviceExploration.ts` |
| GPT Actions bridge | Sperimentale. Adatta bootstrap/action/finalize allo stesso compilatore di contesto e shell. | Consente l'esperimento con ChatGPT senza ridefinire il Core o il ciclo nativo. | `backend/app/plugins/gpt_bridge/`, [Core runtime](core-runtime-contract.md) |
| Agentic Module host + SDK | Preparazione V2, opt-in. Contratti, host a subprocess e kit di conformita'; nessun modulo prodotto installato. | Prepara estensioni future attraverso Core Ports, senza accesso diretto a DB o internals. | `backend/app/agentic_modules/`, `backend/scarlet_agentic_module_sdk/`, [Module contract](agentic-modules-contract.md) |

## Qualita' E Operazioni

| Tecnologia / soluzione | Stato e uso | Motivo della scelta | Fonte tecnica |
|---|---|---|---|
| Pytest, Ruff, mypy | Attivi in sviluppo/CI. Test, lint e type-check focalizzati. | Proteggono contratti deterministici senza scambiare una metrica per una valutazione cognitiva. | `backend/pyproject.toml`, `.github/workflows/quality.yml` |
| Validator documentazione e skill | Attivi in CI. Verificano riferimenti e contratti operativi locali. | Impediscono che indice, skill e documentazione di supporto si disallineino silenziosamente. | `scripts/check_documentation.py`, `scripts/check_project_skills.py` |
| Preflight database | Attivo per operazioni e release. Lettura, integrita' e ruolo prima di modifiche. | Protegge il DB VPS reale da test, copie o deploy che lo trattino come artefatto del codice. | `backend/app/ops/database_preflight.py`, [Database topology](database-topology.md) |

## Regola Di Manutenzione

Aggiorna questa mappa nella stessa modifica che introduce, attiva, sostituisce,
declassa o ritira una scelta tecnica, un provider, un archivio o una soluzione
custom. Aggiungi un documento specifico soltanto quando servono contratti,
configurazioni, misure o procedure non contenibili qui; collega quel documento
dalla riga interessata. Se codice e mappa divergono, correggi la mappa o apri
una decisione: non nascondere una via shadow, sperimentale o incompleta dietro
il nome di una dipendenza installata.
