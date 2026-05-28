# Branch: Memoria

Last updated: 2026-05-28
System version assessed: V1.3.1
Status: active branch

## Filosofia del ramo

La memoria e il sistema con cui Scarlet costruisce continuita: fatti semantici,
episodi, sessioni, summary, provenienza, conflitti, deprecazioni, salienza,
preferenze, checkpoint, emozioni future, knowledge graph e retrieval avanzato.

L'effetto desiderato e che Scarlet ricordi come un agente digitale robusto:
non copiando intere conversazioni nella memoria semantica, ma salvando ancore
riusabili e recuperando le sessioni sorgente quando serve precisione.

## Evidenze

- Memoria semantica con write/search/read/conflicts/deprecate/supersede.
- Memorie collegate a `source_session_id`, `source_turn_id`,
  `source_message_id`.
- Memoria episodica con session summary, transcript e ricerca sessioni.
- Automatic memory context a inizio turno.
- Filtri temporali e sparse retrieval FTS5/BM25.
- Proposal inbox interno per candidati memoria generati da idle review, con
  preflight su duplicati, memorie simili e fatti canonici. La inbox non e
  esposta a Scarlet tramite `mind_api`; viene letta e archiviata solo da API di
  manutenzione.
- Idle maintenance ora risolve i casi cauti nella stessa pipeline: reject e
  duplicate vengono archiviati, create_new molto sicure possono diventare
  memorie attive, e i casi ambigui passano a un solo resolver LLM batch.
- V1.3.0 aggiunge un substrato derivato per retrieval avanzato:
  `memory_surfaces`, `memory_graph_nodes`, `memory_graph_edges` e manifest di
  readiness. Questi indici sono rigenerabili e preparano embedding, Milvus
  shadow mode e knowledge graph senza cambiare la superficie `mind_api`.
- V1.3.1 aggiunge un adapter shadow opzionale sopra `memory_surfaces`.
  Il backend puo confrontare retrieval vettoriale locale deterministico o
  Milvus Lite in trace, senza usare quei punteggi per cambiare il ranking
  attivo.
- Prove live: Scarlet recupera sessioni precedenti, ricorda dati personali e
  usa memoria utente per personalizzazione.
- Limite aperto: salvataggio autonomo non e garantito in ogni caso.

## Stato attuale

Valutazione: L4+.

E il ramo piu avanzato. La combinazione memoria semantica + episodica e gia
innovativa e utile. La proposal inbox ora e un ledger operativo: conserva
candidate, preflight, risoluzioni, scarti e memorie applicate. V1.3.0 prepara
le basi tecniche per dense retrieval e graph expansion con superfici e nodi
derivati e V1.3.1 valida un canale shadow trace-only, ma non cambia ancora il
ranking finale. Non e L5 perche mancano
ancora merge/deprecate automatici, Dream review, compaction, embedding reale,
knowledge graph reasoning, pesi emotivi, staleness scoring e privacy
multiutente vera.

Sistema valutato: V1.3.1.

## Sviluppi precedenti

- Memory v0.
- Lifecycle M2.
- Atomic facts M3.
- Episodic recall M3.5.
- Temporal/sparse retrieval M4 parziale.
- Prompt semantic consolidation.
- Idle maintenance missed-memory review.
- V1.1.0 memory proposal inbox: l'idle review genera proposal persistenti con
  evidenza, azione suggerita, similarita e slot futuri embedding/graph.
- V1.1.1 proposal inbox separation: la consultazione passa alle API di
  manutenzione con paginazione e archiviazione, fuori dalla superficie
  model-facing di Scarlet.
- V1.2.0 cautious proposal resolution: la stessa idle maintenance archivia
  scarti/duplicati, applica create_new molto sicure e manda i casi ambigui a
  un resolver LLM batch opzionale.
- V1.3.0 retrieval readiness: superfici embeddabili per memorie/fatti/sessioni
  e nodi KG, graph nodes/edges per `has_fact`, `about_entity`,
  `evidenced_by_session`, `supersedes`, `superseded_by` e lifecycle fact-edge.
- V1.3.1 retrieval shadow adapter: `local` deterministico e `milvus_lite`
  opzionale sopra `memory_surfaces`, con risultati tracciati in
  `memory.search` e `memory.context` ma non usati per il ranking finale.

## Evolutive

- Dream review ogni 12 ore sull'archivio giornaliero delle proposal risolte o
  rimaste in pending_review.
- Applicazione controllata avanzata delle proposal: merge/update/deprecate.
- Compaction semantica e merge duplicati.
- Stale-memory detection e deprecazione assistita.
- Embedding provider reale per sostituire `local_hash_embedding_v1` come
  esperimento scientificamente valido.
- Milvus Lite/Qdrant in shadow mode con embedding reale sopra
  `memory_surfaces`.
- Hybrid retrieval: sparse + dense embeddings + graph expansion + reranking.
- Knowledge graph con entita, relazioni, salienza, temporalita e staleness.
- Pesi emotivi/affettivi collegati a memorie personali.
- Memoria multiutente separata per profilo.
