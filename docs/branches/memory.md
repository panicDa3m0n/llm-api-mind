# Branch: Memoria

Last updated: 2026-07-13
System version assessed: V1.32.0
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
- V1.29.0 sostituisce il packet automatico ricco con tre liste di hook V2
  (`relevant`, `recent_user`, `recent_general`), deduplicate e navigabili.
- `memory_activities` separa recenza cognitiva append-only da `updated_at`;
  letture sistemiche e consegna automatica non rinfrescano la memoria.
- Ogni hook automatico richiede sessione e messaggio sorgente risolvibili;
  `session message` e `session turn` aprono direttamente l'evidenza.
- Summary mancanti/stale hanno audit e riconciliazione bounded/retryable.
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
- V1.4.0 aggiunge una tassonomia backend-owned delle superfici cognitive:
  Scarlet salva la memoria canonica, mentre il backend genera superfici come
  `memory_text`, `preference_text`, `future_use_text`, `temporal_text`,
  `fact_bundle_text` e `conflict_guard_text` quando applicabile.
- V1.5.0 aggiunge superfici lab per ispezionare maintenance jobs e proposal
  ledger senza esporre questi endpoint a Scarlet tramite `mind_api`.
- V1.5.0 fissa il confine pre/post embedding-KG: merge, update automatico e
  deprecazione automatica aspettano evidenze da embedding/KG.
- V1.10.0 aggiunge il primo adapter cloud embedding reale in shadow:
  OpenRouter `/embeddings` con
  `nvidia/llama-nemotron-embed-vl-1b-v2:free`, cache SQLite
  `embedding_vectors` per superfici stabili indicizzate da content hash e
  rerank opzionale via
  `nvidia/llama-nemotron-rerank-vl-1b-v2:free`.
- V1.11.0 raggruppa dense/rerank per memoria e aggiunge
  `retrieval_hybrid_mode=off|shadow|active`, cosi il ranking ibrido puo essere
  valutato o attivato in modo esplicito su `memory.context` e `memory.search`.
- V1.11.1 aggiunge NetworkX come motore KG attivo leggero per espansione
  associativa. Il backend costruisce un grafo temporaneo da memorie, nodi/edge
  derivati e domini di discorso, quindi espone `retrieval_graph` nei trace e
  nei risultati di ricerca. Il primo caso validato e il recupero della memoria
  sul limite del cioccolato in una richiesta implicita su bevanda serale calda.
- V1.11.2 introduce `memory-packet-v1` per il runtime context model-facing:
  Scarlet riceve claim, provenienza, confidenza/salienza, soggetto cognitivo,
  domini, validita, sensibilita, facts compatti e route di retrieval, mentre i
  segnali completi restano nei trace `memory.context`.
- V1.11.3 stabilizza la coerenza tra superfici e vettori embedding: quando
  OpenRouter crea o recupera da cache un embedding per una `memory_surface`, la
  superficie viene marcata come `embedded` con modello e vector id. Stabilizza
  anche `/mind/memory/facts`: l'`intent` operativo non viene piu usato come
  query dati implicita.
- V1.11.4 stabilizza la canonicalizzazione facts: gli alias brevi vengono
  riconosciuti solo come frasi/token autonomi, `response_format` richiede un
  segnale strutturale esplicito, e il DB laboratorio archivia i facts rumorosi
  generati dal vecchio matching substring.
- V1.12.0 stabilizza le superfici di retrieval con una policy role-aware:
  superfici di contenuto e fatti canonici possono promuovere una memoria,
  mentre `future_use_text`, `temporal_text` e `conflict_guard_text` restano
  supporto/corroborazione e non possono selezionare una memoria da sole.
- V1.15.0 stabilizza i campi cognitivi della memoria:
  `type` e `scope` sono label semantiche permissive, `confidence` e
  `salience` diventano legacy/audit e non ranking attivo, `tags`/`metadata`
  non sono piu' campi normali da far compilare a Scarlet, e la search manuale
  e cross-scope salvo filtro esplicito.
- V1.15.0 aggiunge superfici interne `content_chunk_text` per content lunghi e
  endpoint `POST /mind/memory/graph` per navigare il KG da una memoria
  recuperata.
- V1.23.0 stabilizza la distinzione tra conflitti veri e somiglianze:
  `memory.conflicts` espone come conflitti solo divergenze tra facts atomici
  attivi, mentre tag/token/exact-content overlap diventa `related_overlap`
  per manutenzione e debug.
- V1.23.0 compatta i risultati model-facing di `memory search` nella shell:
  Scarlet riceve memorie, provenienza, facts compatti, segnali di retrieval e
  trace id; i dump completi di embedding shadow, KG e hybrid ranking restano
  nei trace.
- V1.25.4 chiarisce il confine shell/endpoint: `memory.facts.backfill` resta
  manutenzione interna per rigenerare facts e artefatti di retrieval dopo
  cambiamenti di extractor/schema/lifecycle, non comando cognitivo normale per
  Scarlet.
- Il probe live corretto del 2026-07-09 conferma che la memoria automatica
  puo recuperare preferenze cross-session senza tool manuale, ma apre bug
  separati su temporal recall non esaustivo, alias shell per `memory write`, e
  applicazione immediata dello stile comunicativo (`BUG-0057`, `BUG-0060`,
  `BUG-0061`).
- V1.13.0 introduce `CODEX_TEST` come isolamento DB per esperimenti: il backend
  puo aprire una copia seedata del DB Scarlet e usare gli stessi endpoint reali
  senza mutare il DB produzione/laboratorio.
- V1.27.0 separa il meccanismo `CODEX_TEST` dal ruolo del DB: `test` e
  `preliminary` possono scrivere solo copie disposable, mentre produzione e
  laboratorio restano fonti non mutabili per le suite. Il vecchio
  `codex_test.db` diventa artefatto storico; l'evaluator crea ora un run DB
  marcato e fresco dalla baseline congelata.
- V1.28.0 divide il monolite repository per dominio senza cambiare la facciata
  usata da memoria, retrieval, shell, chat e manutenzione: stato canonico,
  facts/proposal lifecycle e artefatti derivati hanno ora confini di codice
  leggibili ma lo stesso contratto transazionale.
- V1.31.0 separa recall e giudizio: FTS, embedding, KG ed euristiche trovano
  candidati; il reranker memory-level e l'unico arbitro finale in modalita
  attiva e il sistema fallisce chiuso quando non e disponibile.
- Prove live: Scarlet recupera sessioni precedenti, ricorda dati personali e
  usa memoria utente per personalizzazione.
- V1.14.4 aggiunge una mitigazione prompt per MiniMax M3: Scarlet deve trattare
  `body={}` nei memory write come mancato salvataggio, usare la guida endpoint
  per un solo retry materialmente corretto e fermare loop identici senza
  dichiarare persistenza.
- Limite aperto: salvataggio autonomo non e garantito in ogni caso.

## Stato attuale

Valutazione: L4+.

E il ramo piu avanzato. La combinazione memoria semantica + episodica e gia
innovativa e utile. La proposal inbox ora e un ledger operativo: conserva
candidate, preflight, risoluzioni, scarti e memorie applicate. V1.3.0 prepara
le basi tecniche per dense retrieval e graph expansion con superfici e nodi
derivati, V1.3.1 valida un canale shadow trace-only e V1.4.0 arricchisce le
superfici cognitive che un embedding dovra leggere. V1.10.0 porta il primo
embedding cloud reale dentro lo stesso canale shadow, con rerank opzionale e
cache delle superfici; V1.11.0 aggiunge grouping memory-level e promozione
ibrida configurabile. V1.15.0 rimuove una fonte importante di rumore
architetturale: i punteggi statici scritti dal modello non governano piu'
il ranking, mentre chunk, KG dinamico e search cross-scope rendono il retrieve
piu coerente con il linguaggio naturale. V1.5.0 migliora la governabilita della manutenzione:
e possibile vedere job, code, conteggi e proposal recenti da API evaluator
senza creare nuovi strumenti cognitivi per Scarlet. V1.11.1 porta il primo KG
associativo attivo con NetworkX: e utile per richiamo human-like per campo di
discorso, ma non e ancora KG reasoning maturo. Non e L5 perche mancano ancora
merge/deprecate automatici, Dream review, compaction, KG entity resolution,
pesi emotivi, staleness scoring, enrichment maturo di tags/facts/metadata e
privacy multiutente vera.

Sistema valutato: V1.32.0.

Aggiornamento V1.31.0:

- Sparse, dense, NetworkX e matching lessicale/entita sono route di recall e
  non possono piu dichiarare una memoria rilevante.
- I candidati sono interleavati round-robin e deduplicati per `memory_id`,
  evitando una fusione con coefficienti manuali.
- Il reranker riceve documenti memory-level basati su contenuto canonico e
  facts attivi; solo gli elementi sopra la soglia query-time diventano
  `selected` o risultati della ricerca manuale.
- `retrieval_hybrid_mode=active` e fail-closed. Errori di configurazione o
  provider producono `final_rerank_unavailable`, non fallback deterministico.
- I punteggi dei motori di recall restano nei trace per osservabilita. La chiave
  `retrieval_hybrid` e mantenuta temporaneamente per compatibilita evaluator,
  ma descrive la nuova policy e dichiara `legacy_weighted_fusion=false`.

Aggiornamento V1.25.4:

- Le capability model-facing del runtime derivano dal registro `mind_shell`,
  non dalla lista delle rotte legacy `/mind/*`.
- `memory.facts.backfill` e marcata `internal_maintenance_only`: utile per
  riallineare facts canonici e artefatti derivati, ma da non proporre a Scarlet
  come comando conversazionale.
- Il registry shell richiede ora i campi lifecycle effettivamente necessari:
  deprecate/supersede devono includere reason, evitando che metacognition o
  help considerino validi comandi destinati a fallire.

Aggiornamento V1.23.0:

- `mind_shell memory search` usa un profilo compatto model-facing per evitare
  che diagnostica di retrieval pensata per evaluator saturi o confonda Scarlet.
- `memory.context.conflicts` non usa piu overlap lessicale/tag come conflitto:
  solo facts atomici divergenti arrivano come conflitti cognitivi.
- `related_overlaps` resta disponibile come segnale di manutenzione per futuri
  job di deduplica/update/deprecazione.
- Hybrid ranking attenua candidati base deboli: una memoria sale in ranking
  attivo quando il contenuto/fact/sparse/entity/tag/graph forte oppure
  dense/rerank la supportano realmente.

Aggiornamento V1.15.0:

- `POST /mind/memory/write` chiede a Scarlet solo nucleo semantico:
  `type`, `scope`, `content`, `reason_for_storage`, `expected_future_use`.
- `confidence`, `salience`, `tags` e `metadata` inviati da prompt vecchi
  vengono preservati solo in audit metadata e non diventano ranking attivo.
- Search manuale: `scope` default cross-scope; `types` restano hint semantici
  ma non vengono fusi nel testo query, evitando falsi positivi da categorie
  generiche.
- Ranking ibrido: stored confidence/salience hanno peso 0; relevance e
  confidence operative sono query-time.
- KG: eliminati domini cablati statici; i concetti derivano da memoria, facts,
  type, scope, sessioni e lifecycle. Scarlet puo' aprire
  `/mind/memory/graph` quando una memoria sembra parte di un cluster piu ampio.
- Test: backend completo verde (`86 passed`), inclusi A/B guard su salience
  statica e content chunks.

Aggiornamento V1.14.4:

- Due sessioni live MiniMax M3 hanno mostrato memory write autonomi con
  `body={}` ripetuto. Il backend e il DB prod erano corretti; il problema resta
  nella generazione tool-use M3/prompt/runtime.
- Il prompt ora chiarisce che `intent` non sostituisce `body`, che un body
  vuoto non e un tentativo valido di scrittura, e che retry identici vanno
  fermati dopo recovery guidata.
- Stato: mitigazione in monitoraggio. Se il prossimo test produce ancora
  `body={}`, il fix dovra passare dal contratto tool/provider, non da ulteriore
  pressione prompt.

Aggiornamento V1.11.0:

- `retrieval_shadow` ora espone sia raw surface results sia
  `grouped_results` deduplicati per memoria.
- OpenRouter rerank produce anche `rerank.grouped_results` su candidati
  memory-level, evitando che superfici duplicate della stessa memoria dominino
  il secondo stadio.
- `retrieval_hybrid_mode=off|shadow|active` permette di tenere il sistema
  invariato, calcolare punteggi ibridi solo per debug, oppure usare davvero
  sparse/base/dense/rerank/salienza/confidenza per ordinare `memory.context` e
  `/mind/memory/search`.
- Default ancora `off`: l'attivazione reale richiede scelta esplicita e,
  per OpenRouter, `OPENROUTER_API_KEY` nell'ambiente.

Aggiornamento V1.11.1:

- `networkx` e dipendenza backend standard, non opzionale.
- `retrieval_graph` viene calcolato in automatico per `memory.context` e
  `/mind/memory/search`.
- Il grafo usa domini backend-owned come `food_drink_wellbeing` ed
  `energy_sleep_focus` come ponti associativi, evitando mapping one-off del tipo
  parola specifica -> memoria specifica.
- Quando una richiesta personale produce evidenza associativa utente, memorie
  progetto base-only vengono declassate per evitare che il ramo progetto copra
  il ramo personale.
- Smoke reale V1.11.1: richiesta "bevanda serale calda ... senza caffeina" ha
  selezionato solo le memorie utente su caffeina/sonno e cioccolato/limite
  corporeo, con `retrieval_graph` esplicito.

Aggiornamento V1.11.2:

- Il pacchetto model-facing delle memorie selezionate e ora compatto e
  operativo. Non include piu metadata grezza, soglie/pesi completi, `signals`
  verbose o trace debug ripetuti.
- I parametri cognitivi attivi sono funzionali solo se cambiano il comportamento
  di Scarlet:
  - `subject`: definisce se la memoria riguarda utente attivo, comportamento di
    Scarlet o progetto/sistema;
  - `domains`: collega il ricordo a domini di retrieval, scope, tipo e tag;
  - `validity`: indica stato attivo/deprecato e future finestre temporali da
    facts;
  - `sensitivity`: orienta cautela e privacy senza inventare diagnosi;
  - `retrieval.routes`: spiega se il ricordo e arrivato da sparse, grafo,
    embedding o rerank.
- Questi campi non sono pensati come cosmetica: devono aiutare applicazione,
  source discipline, privacy futura, debug e ranking. Campi piu ricchi come
  `applies_when`, `do_not_apply_when`, peso emotivo e staleness vanno derivati
  da facts/KG/maintenance quando potranno essere mantenuti in modo affidabile.

Aggiornamento V1.11.3:

- Le `memory_surfaces` ora riflettono lo stato reale degli embedding OpenRouter:
  sia cache miss sia cache hit aggiornano `embedding_status`, `embedding_model`
  ed `embedding_vector_id`.
- `/mind/memory/facts` usa solo `memory_id`, `entity`, `predicate`, `query`,
  `status` e `include_inactive` forniti nel body. L'`intent` resta tracciamento
  operativo e non diventa mai un filtro dati implicito.
- Questo riduce due fonti di confusione per Scarlet e per il debug: superfici
  falsamente pending e facts apparentemente vuoti perche filtrati da intent
  descrittivi troppo generici.

Aggiornamento V1.11.4:

- Gli alias noti dei facts ora usano matching per frase/token, non substring:
  `sal` continua a funzionare come alias di `sal-updates`, ma non dentro parole
  come `segnala` o `salutare`.
- `response_format` non viene piu inferito dalla sola parola generica
  `response/risposta`; richiede tag/metadata espliciti, blocchi, o frasi come
  "answer with" / "rispondere con".
- Il DB laboratorio e stato riconciliato: 7 facts attivi non piu supportati
  dal nuovo estrattore sono stati marcati `rejected_extractor_noise`, 6 facts
  sostitutivi supportati sono stati creati, e gli artifact fact-derived
  collegati ai facts respinti sono stati rimossi dai percorsi attivi.

Aggiornamento V1.12.0:

- `memory_text` e superfici type-specific sono ora content-focused: non
  inglobano piu `reason_for_storage` o `expected_future_use`.
- Sparse/lexical e NetworkX domain matching usano contenuto, tipo, scope, tag
  e facts, evitando che il testo sul "quando usare" una memoria diventi
  evidenza primaria.
- `retrieval_shadow.grouped_results` passa a
  `memory_target_role_aware_surface_score_v2` ed espone:
  `surface_roles`, `promotable_surface_kinds`, `support_surface_kinds`,
  `promotable_score`, `support_score` e `active_rank_eligible`.
- Il rerank grouped riceve solo candidati promuovibili. Le superfici
  ausiliarie restano nei trace come supporto, ma non possono convincere da sole
  il ranker ibrido.

Aggiornamento V1.13.0 - dirty Codex test DB:

- `codex_test.db` e stato popolato partendo dal DB reale Scarlet e aggiungendo
  240 memorie controllate rumorose piu una coppia lifecycle
  old/current tramite i normali endpoint `/mind/call` e `/mind/memory/write`.
- Stato dopo il primo run:
  - DB prod: 30 memorie, 241 superfici, 236 embedding, 90 nodi KG, 75 edge KG;
  - DB test: 272 memorie, 242 memorie codex-test, 2.507 superfici, 521
    embedding, 671 nodi KG, 725 edge KG.
- Suite retrieval iniziale:
  - 6/9 probe superati con OpenRouter shadow completato e hybrid retrieval
    attivo;
  - punti forti: richiamo diretto cioccolato, richiamo associativo bevanda
    serale/caffeina/cioccolato, controllo negativo musica/cucina, schema API,
    privacy/runtime, lifecycle corrente;
  - limiti: recall cross-language di lezioni metacognitive e ponte
    memoria-sessione non ancora sufficientemente robusti; una preferenza
    reale del DB prod puo battere il duplicato controllato e va misurata come
    equivalenza funzionale separata dal recall esatto del dataset.
- Evidenza report:
  `backend/app/evals/runs/20260619_161039_codex_test_memory/`.

Aggiornamento V1.13.0 - corrected context eval:

- Il metodo di test e stato corretto: la valutazione principale non usa piu
  solo `/mind/memory/search`, ma il percorso reale
  `/api/chat/sessions/{id}/turn/stream`, catturando il `memory_context`
  automatico che Scarlet riceve prima della risposta.
- Run corretto:
  `backend/app/evals/runs/20260619_172206_codex_test_memory/`.
- Run live MiniMax M3 con gli stessi cinque prompt:
  `backend/app/evals/runs/20260619_172536_codex_live_scarlet_memory/`.
- Conferme:
  - memoria semantica -> sessione episodica funziona davvero quando il
    contesto automatico seleziona la memoria con `source_session_id`;
  - MiniMax M3 usa correttamente il ponte e ha aperto la sessione sorgente nel
    test live;
  - preferenze comunicative "stanco/asciutto" vengono recuperate e applicate.
- Debolezze reali:
  - la richiesta "bevanda serale senza caffeina" recupera la caffeina ma non
    porta sempre anche il limite cioccolato come vincolo associativo vicino;
  - il retrieval metacognitivo privilegia lezioni duplicate/generiche
    "memoria come ancora" invece della lezione effort-routing;
  - il controllo negativo jazz/cucina riceve ancora una memoria progettuale
    non pertinente per overlap debole.
- Valutazione: il modello M3 spesso compensa bene il rumore, ma il sistema non
  deve dipendere dalla capacita del modello di ignorare memorie sbagliate.

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
- V1.4.0 memory surface taxonomy: compilatore deterministico backend per
  superfici cognitive derivate da memoria, fatti e provenance; assessment
  maintenance nei `decision_json` delle proposal per classificare lane e focus
  di review senza cambiare le soglie di auto-apply.
- V1.5.0 maintenance lab: `GET /api/maintenance/overview`,
  `GET /api/maintenance/jobs` e `POST /api/maintenance/jobs/{job_id}/run` per
  ispezionare e attivare manualmente job pending in laboratorio.
- V1.5.0 roadmap boundary: `docs/memory-roadmap.md` distingue cosa va avanti
  prima degli embedding/KG e cosa deve attendere la macchina Windows/GPU.
- V1.10.0 OpenRouter cloud embedding shadow: backend
  `retrieval_shadow_backend=openrouter`, cache `embedding_vectors`, dense
  results e rerank opzionale dentro `retrieval_shadow`, con policy
  `trace_only_no_active_ranking`.
- V1.11.0 active hybrid retrieval calibration: grouping memory-level dei
  risultati dense/rerank, ranker ibrido configurabile e test backend su
  parafrasi italiana, controllo negativo e contesto automatico chat.
- V1.11.1 NetworkX associative retrieval: espansione KG leggera, candidate
  surface fetch meno stretto per il percorso embedding, gating personale/progetto
  e test su richiamo implicito di vincoli personali.
- V1.11.2 compact model-facing memory packets: `memory-packet-v1` riduce rumore
  nel runtime context, mantenendo full debug nei trace.
- V1.11.3 memory retrieval/facts consistency: allineamento surface/vector cache
  e separazione netta tra intent operativo e query dati per facts.
- V1.11.4 fact canonicalization stabilization: matching alias con confini di
  frase/token, `response_format` piu stretto, e cleanup DB dei facts rumorosi.
- V1.12.0 role-aware retrieval surfaces: superfici contenuto/facts come
  segnali primari, superfici future-use/temporali/lifecycle come supporto
  non promuovibile.
- V1.13.0 Codex test database isolation: flag di bootstrap `CODEX_TEST` con
  seed one-shot da DB reale e visibilita in health/dashboard.
- V1.13.0 dirty memory harness: popolazione Codex test DB, lifecycle probe e
  suite iniziale su direct, associative, metacognitive, episodic, privacy,
  API-schema, lifecycle e negative-control retrieval.
- V1.13.0 corrected context-vs-live eval: cinque prompt eseguiti prima sul
  contesto automatico con provider fake e poi su Scarlet reale/MiniMax M3,
  distinguendo giudizio sistema da giudizio modello.
- V1.15.0 memory field stabilization: free semantic `type`/`scope`,
  cross-scope manual search, static confidence/salience neutralized,
  tags/metadata moved out of the normal Scarlet write contract, internal
  content chunks, dynamic KG concepts, and `/mind/memory/graph` navigation.

## Verifica V1.32.0

- Implementazione: memoria semantica, fatti, episodica, lifecycle, attivita
  cognitiva, provenance, summary, sparse/KG/dense-shadow/hybrid retrieval,
  proposal e maintenance.
- Test deterministici: include API, shell, storage, context V2, maintenance,
  casi reali congelati e contratti final-arbiter su rigetto, recall cross-route
  e fail-closed.
- Evidenza Scarlet: recall automatico/manuale, navigazione sorgente,
  personalizzazione cross-session e write provenance verificati; restano
  fallimenti comportamentali del modello.
- Integrazione runtime: retrieval ricco interno e hook V2 compatti sono sempre
  costruiti; la configurazione `active` usa OpenRouter rerank come dipendenza
  esplicita e non assume fallback deterministico.
- Produzione: 46 memorie storiche riparate deterministicamente; 242 restano
  senza evidenza sufficiente e non devono essere inventate. Summary eleggibili
  riconciliate, con maintenance ordinaria a 15 minuti.
- Prossimo gate: misurare candidate coverage, latenza, disponibilita e soglia
  del final rerank su DB completo; poi separare evidence detection da
  adjudication per duplicati/conflitti e introdurre ownership utente reale.
- Prima calibrazione live V1.31.0: le soglie `0.55` e `0.40` hanno respinto
  rispettivamente una memoria personale prevista a `0.465327` e un match
  Zero-Luce quasi letterale a `0.089455`. Il controllo negativo osservato
  resta sotto `0.0004`; la soglia corrente e quindi `0.01`, ancora provvisoria
  e soggetta a controlli positivi/negativi piu ampi.
- Episodic shell V1.32: `session list` non nasconde piu risultati oltre il
  limite interno 500, query e filtri temporali lavorano sull'indice completo,
  e il fallback summary usa il transcript completo anche quando `session open`
  restituisce una finestra limitata. MiniMax M3 ha usato una ricerca sessioni,
  una ricerca memoria e tre transcript completi per ricostruire una catena
  storica reale.

## Evolutive

- Backlog dettagliato dei fix candidati sui campi cognitivi della memoria:
  `docs/branches/memory-field-fix-backlog.md`.
- Dream review ogni 12 ore sull'archivio giornaliero delle proposal risolte o
  rimaste in pending_review.
- Applicazione controllata avanzata delle proposal: merge/update/deprecate.
- Compaction semantica e merge duplicati.
- Stale-memory detection e deprecazione assistita.
- Test live OpenRouter final-rerank su query italiane, sinonimi, parafrasi,
  negative control e ambiguita per calibrare candidate pool e soglia.
- Dashboard/lab view per confrontare raw surfaces, grouped dense, grouped
  rerank e selected/near_miss/excluded nello stesso turno.
- Milvus Lite/Qdrant in shadow mode con embedding reale sopra
  `memory_surfaces`.
- Recall multi-route: sparse + dense embeddings + NetworkX graph expansion,
  seguito da final rerank memory-level.
- Knowledge graph maturo con entita, relazioni, salienza, temporalita,
  staleness e percorsi spiegabili oltre ai domini leggeri V1.11.1.
- Pesi emotivi/affettivi collegati a memorie personali.
- Parametri cognitivi avanzati derivati e verificabili:
  `applies_when`, `do_not_apply_when`, `emotional_weight`, `staleness`,
  `durability`, `privacy_class`, `relationship_anchor`. Devono nascere da
  facts, KG, manutenzione o evidenze sessione, non da campi compilati
  liberamente dall'agente.
- Memoria multiutente separata per profilo.
- Lab dashboard per pending proposal, job falliti/skippati e memorie create da
  maintenance, mantenendo queste superfici fuori dal `mind_shell`
  model-facing.
