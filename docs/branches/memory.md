# Branch: Memoria

Last updated: 2026-05-25  
System version assessed: V1.1.0
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
- Proposal inbox per candidati memoria generati da idle review, con preflight
  su duplicati, memorie simili e fatti canonici.
- Prove live: Scarlet recupera sessioni precedenti, ricorda dati personali e
  usa memoria utente per personalizzazione.
- Limite aperto: salvataggio autonomo non e garantito in ogni caso.

## Stato attuale

Valutazione: L4+.

E il ramo piu avanzato. La combinazione memoria semantica + episodica e gia
innovativa e utile. La proposal inbox porta la manutenzione fuori dal solo
diagnostico, senza ancora auto-scrivere memorie attive. Non e L5 perche mancano
applicazione controllata delle proposal, compaction, embedding, knowledge
graph, pesi emotivi, staleness scoring e privacy multiutente vera.

Sistema valutato: V1.1.0.

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

## Evolutive

- Applicazione controllata delle proposal: approva/rifiuta/applica/merge.
- Compaction semantica e merge duplicati.
- Stale-memory detection e deprecazione assistita.
- Hybrid retrieval: sparse + dense embeddings + reranking.
- Knowledge graph con entita, relazioni e salienza.
- Pesi emotivi/affettivi collegati a memorie personali.
- Memoria multiutente separata per profilo.
