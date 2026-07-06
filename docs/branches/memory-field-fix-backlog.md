# Memory Field Fix Backlog

Last updated: 2026-06-23
Status: V1.15.0 implemented core fixes, future enrichment still open
Branch: Memoria
System baseline discussed: V1.14.x laboratory state
Implementation checkpoint: `docs/checkpoints/v1.15.0-memory-fields-checkpoint.md`

Questo documento conserva le decisioni e i fix candidati emersi dalla
discussione sui campi cognitivi della memoria. Non descrive codice gia'
deciso per implementazione immediata: serve a non perdere il ragionamento, a
rendere ogni punto discutibile, e a mantenere gli interventi futuri piccoli,
reversibili e misurabili.

Nota V1.15.0:

- Implementati: `type` e `scope` come label semantiche permissive,
  default search cross-scope, `confidence`/`salience` disattivati dal ranking
  attivo e rimossi dal pacchetto model-facing, `tags`/`metadata` non piu'
  agent-supplied attivi, chunk interni del content, KG navigabile via
  `/mind/memory/graph`, e test A/B per salience statica e content chunk.
- Rimasti futuri: enrichment robusto di tag/metadata/facts, entity resolution
  KG matura, embedding dei chunk sessione, jobs dedicati di manutenzione
  avanzata e navigazione KG piu' guidata da prompt dopo ulteriori test live.

Formato di ogni punto:

- Mio punto di vista: da cosa nasce la richiesta del project owner.
- Tuo punto di vista: criticita' o cautele rilevate da Codex/Scarlet.
- Sistema attuale: come funziona oggi, senza dettaglio codice.
- Fix necessari: todo progettuali, non implementazione.

## Principi guida emersi

- Scarlet deve compilare meno campi possibile durante il salvataggio diretto.
- Il backend deve possedere e derivare tutto cio' che puo' essere determinato,
  normalizzato o arricchito senza chiedere al modello live.
- I campi salvati non devono diventare classificatori statici quando la loro
  utilita' reale dipende dalla query corrente.
- Il retrieve deve comportarsi in modo human-like: ricordo diretto da content,
  associazione tramite KG, restrizione temporale quando serve, e rerank finale
  sulla richiesta corrente.
- I pacchetti consegnati a Scarlet devono essere puliti: molti indici interni
  servono al retrieve, ma non devono diventare rumore nel contesto del modello.

## Esito implementazione V1.15.0

- `type`: reso label semantico permissivo, con esempi nel prompt e alias
  compatibili; non e' piu' un enum chiuso che blocca sinonimi futuri.
- `scope`: reso label semantico permissivo; default memoria `general`, search
  manuale cross-scope se Scarlet non specifica uno scope.
- `content`: aggiunte superfici interne `content_chunk_text` per memorie lunghe;
  Scarlet riceve comunque una sola memoria deduplicata.
- `reason_for_storage` e `expected_future_use`: mantenuti agent-supplied ma
  trattati come supporto, non come selettori autonomi.
- `confidence` e `salience`: direct write di Scarlet li ignora per ranking,
  salva valori neutrali legacy e conserva eventuali input vecchi solo in audit.
- `tags` e `metadata`: rimossi dal contratto normale di Scarlet; eventuali
  valori inviati da prompt vecchi finiscono in audit metadata, non in campi
  attivi.
- `usage_count` e temporali: invariati, backend-owned.
- `memory_facts`: resta estrazione conservativa; non vengono inventate entita'
  generiche quando mancano ancore affidabili.
- `memory_surfaces`: aggiornate con chunk interni e senza segnali statici di
  confidence/salience.
- `embedding_vectors`: invariati come storage/cache, ma il ranking non usa piu'
  punteggi statici della memoria.
- `KG`: eliminati domini cablati; concetti dinamici derivano da memoria, type,
  scope, facts, sessioni e lifecycle. Aggiunto endpoint
  `POST /mind/memory/graph` per navigazione.
- `memory_proposals`: auto-apply deterministico per `create_new` sicuri;
  resolver LLM resta per proposal ambigue; proposal archiviate mantengono
  snapshot per review futura.

## Type

### Mio punto di vista

Il campo `type` non dovrebbe richiedere un dizionario rigido sempre piu'
grande. L'embedding puo' risolvere sinonimi e tipi semanticamente vicini senza
aggiungere un nuovo campo da far compilare a Scarlet. Scarlet deve ricevere
esempi nel system prompt, ma il sistema dovrebbe poter accettare varianti e
recuperare comunque memorie affini per similarita'.

### Tuo punto di vista

La direzione e' interessante e va resa sperimentale e reversibile. La criticita'
e' che oggi il tipo non e' solo testo: governa filtri, superfici type-specific,
validazioni API, search manuale e parte del comportamento di manutenzione. Se
diventa troppo libero senza una strategia di compatibilita', rischia di
rompere filtri e dashboard.

### Sistema attuale

Il backend accetta un set chiuso di tipi cognitivi e normalizza alcuni alias.
Il tipo viene salvato nella memoria, usato per filtri, search, superfici
specifiche e classificazione del pacchetto memoria. Se Scarlet invia un tipo
non previsto, oggi la chiamata puo' fallire.

### Fix necessari

- Progettare un esperimento reversibile per rendere `type` piu' permissivo.
- Mantenere nel prompt esempi forti di tipi attesi, ma non trattarli come
  dizionario esaustivo.
- Embeddare il valore di `type` come segnale semantico di retrieve.
- Evitare matching testuale rigido sul type quando e' disponibile similarita'
  semantica.
- Definire come generare superfici type-specific quando il type non e'
  canonico.
- Aggiungere metriche per capire se type libero migliora o peggiora:
  errori di salvataggio, rumore nei retrieve, tipi degenerati, duplicati
  semantici.
- Tenere documentato un rollback: ripristino del set chiuso se il type libero
  aumenta caos o regressioni.

## Scope

### Mio punto di vista

Lo scope non deve servire a privacy, accessi o isolamento multiutente. Quando
arriveranno utenti reali, il backend filtrera' prima per `user_id` tramite
sessione login. Lo scope deve rappresentare lo scopo o area della memoria, e
puo' quindi essere piu' libero e gestito via embedding come il type.

### Tuo punto di vista

Accolgo la correzione: usare `scope` come controllo privacy sarebbe sbagliato
nel progetto attuale. La criticita' e' che oggi `scope` viene usato come filtro
rigido di ricerca; renderlo libero senza cambiare search e contesto automatico
potrebbe peggiorare il recall.

### Sistema attuale

Lo scope e' un campo vincolato, usato nei filtri di memoria. La search manuale
ha default orientato al progetto, mentre il retrieval automatico cerca in modo
piu' ampio. Questa divergenza puo' far perdere memorie personali nelle ricerche
manuali.

### Fix necessari

- Correggere il default della search manuale: nessun default restrittivo su
  `project`; ricerca cross-scope salvo richiesta esplicita.
- Separare concettualmente lo scope cognitivo dal futuro controllo utente.
- Pianificare un campo backend-owned futuro `user_id` o equivalente per
  isolamento dati, fuori da `scope`.
- Valutare scope libero o semi-libero come superficie embeddabile.
- Evitare che uno scope libero diventi filtro rigido non controllato.
- Aggiornare prompt e schema quando il comportamento sara' definito, chiarendo
  che scope descrive lo scopo cognitivo della memoria, non la privacy.

## Content

### Mio punto di vista

Il content deve essere ricercabile sia come memoria intera sia come frasi
interne, soprattutto quando il content e' lungo. Se piu' frasi della stessa
memoria matchano, il backend deduplica per memory id e consegna a Scarlet una
sola memoria pulita.

### Tuo punto di vista

La proposta e' forte se implementata come multi-vector controllato. Non deve
sostituire l'embedding del content intero: deve affiancarlo. Frasi troppo
piccole possono perdere contesto, quindi serve una policy di chunking sobria.

### Sistema attuale

Il content canonico della memoria viene salvato come testo principale. Il
backend genera superfici derivate per retrieve ed embedding, ma non esiste
ancora una strategia completa di embedding per frasi atomiche del content.

### Fix necessari

- Introdurre superfici derivate di tipo content chunk/claim solo per content
  lunghi o multi-concetto.
- Conservare sempre anche l'embedding del content completo.
- Deduplicare i risultati per memory id prima di costruire il pacchetto per
  Scarlet.
- Consegnare a Scarlet la memoria madre una sola volta.
- Includere, se utile, un breve match evidence o snippet della frase che ha
  attivato il retrieve, senza esporre tutte le superfici interne.
- Testare casi con content lungo, frasi ambigue, frasi adiacenti e query
  parafrasate.

## Reason For Storage

### Mio punto di vista

Al momento non emergono richieste di modifica.

### Tuo punto di vista

Il campo resta utile come spiegazione del perche' la memoria esiste, ma non
deve diventare fonte primaria di retrieve.

### Sistema attuale

Scarlet o manutenzione compilano `reason_for_storage`. Il backend lo usa per
tracciare il razionale e per generare superfici di supporto.

### Fix necessari

- Mantenerlo nel contratto se resta davvero utile a Scarlet per capire la
  memoria.
- Assicurare che non promuova una memoria da solo nel ranking.
- Valutare in futuro se puo' essere compilato o riscritto da manutenzione per
  maggiore coerenza.

## Expected Future Use

### Mio punto di vista

Al momento non emergono richieste di modifica.

### Tuo punto di vista

Il campo e' utile se aiuta Scarlet a capire quando riusare la memoria, ma puo'
diventare rumoroso se scritto largo.

### Sistema attuale

Scarlet o manutenzione lo compilano. Il backend lo usa come superficie
ausiliaria di future-use, non come verita' primaria.

### Fix necessari

- Mantenerlo come supporto, non come segnale promotore autonomo.
- Valutare se spostarlo progressivamente verso manutenzione/enrichment.
- Testare se migliora davvero l'applicazione della memoria o se crea richiami
  troppo larghi.

## Confidence e Salience

### Mio punto di vista

Non dovrebbero essere salvati come campi statici compilati da Scarlet. Sono
punteggi relativi alla query corrente, quindi devono nascere durante il
retrieve/rerank. Se Scarlet li salva, rischia di inventare numeri asettici e
sporcare il ranking.

### Tuo punto di vista

Concordo sulla critica principale. L'unica cautela e' la compatibilita' con lo
storico e con le pipeline che oggi li usano. La transizione dovrebbe essere
graduale: prima smettere di farli pesare nel ranking, poi rimuoverli dal
contratto model-facing.

### Sistema attuale

Scarlet/manutenzione inviano `confidence` e `salience`. Il backend li salva,
li valida e oggi possono pesare nel ranking. Questo rende il punteggio statico,
anche se la rilevanza reale cambia da query a query.

### Fix necessari

- Deprecare `confidence` e `salience` come campi compilati da Scarlet.
- Rimuoverli dal prompt/schema model-facing quando il backend e' pronto.
- Impostare valori legacy neutrali o ignorarli nel ranking attivo.
- Spostare il calcolo di punteggi in runtime:
  - relevance rispetto alla query;
  - confidence del retrieve;
  - salience del candidato nella risposta corrente.
- Fare decidere al rerank il peso finale sulle memorie candidate.
- Conservare i campi storici solo per backward compatibility o audit fino a
  migrazione conclusa.
- Aggiornare test per verificare che memorie con salience storica alta non
  battano memorie piu' rilevanti per la query.

## Tags

### Mio punto di vista

Scarlet non deve inserirle e nemmeno suggerirle. Le tags vanno generate da
processi di manutenzione/enrichment sul content. Se non dimostrano benefici
misurabili su retrieve e performance, potranno essere rimosse.

### Tuo punto di vista

Concordo. Le tags sono economiche e leggibili, ma agent-supplied sono
irregolari. Meglio trattarle come dato derivato e manutentivo.

### Sistema attuale

Scarlet puo' passare tags nel salvataggio. Il backend le normalizza e le usa in
ricerca, facts, alias e superfici. Nel DB reale molte memorie importanti hanno
tags vuote o disomogenee.

### Fix necessari

- Rimuovere `tags` dal carico obbligatorio o atteso di Scarlet.
- Spostare generazione e normalizzazione tags in job di manutenzione.
- Misurare se tags migliorano davvero retrieve, KG, facts o explainability.
- Definire policy per deprecazione tags se non portano beneficio.
- Evitare che tags diventino fonte canonica: devono restare indice derivato.

## Metadata

### Mio punto di vista

Come per le tags, meglio non farli compilare a Scarlet. I metadata servono per
audit, lifecycle e manutenzione, quindi devono essere backend/maintenance-owned.

### Tuo punto di vista

Concordo. Il metadata libero e' utile per audit, ma pericoloso se diventa
canale cognitivo non controllato o dumping ground per errori del modello.

### Sistema attuale

Il backend accetta `metadata` e sposta anche campi extra del modello dentro
`metadata.model_extra`. I processi di manutenzione usano metadata per proposal,
risoluzioni e lifecycle.

### Fix necessari

- Togliere `metadata` dal contratto normale di Scarlet.
- Mantenere metadata come spazio backend-owned per audit e lifecycle.
- Pulire o ignorare `model_extra` non utile nei pacchetti model-facing.
- Definire quali metadata possono generare superfici o KG, e quali restano solo
  audit.
- Aggiungere job di manutenzione per compattare o normalizzare metadata troppo
  rumorosi.

## Usage Count

### Mio punto di vista

Non deve essere usato nel retrieve. Deve servire solo per manutenzione,
analisi e possibili funzioni innovative sulla vita delle memorie.

### Tuo punto di vista

Concordo. Usarlo in ranking creerebbe popularity bias. E' invece molto utile
per capire memorie vive, dormienti, mai usate o troppo centrali.

### Sistema attuale

Il backend incrementa `usage_count` quando una memoria viene selezionata/usata.
Non e' il criterio centrale del retrieve attuale.

### Fix necessari

- Mantenere usage fuori dal ranking attivo.
- Usarlo nei job di manutenzione:
  - memorie mai usate;
  - memorie ricorrenti;
  - memorie centrali da consolidare;
  - memorie vecchie ancora vive;
  - memorie sospette se usate troppo spesso in contesti non pertinenti.
- Creare report o dashboard lab per usage analysis.

## Memory Facts

### Mio punto di vista

Il concetto e' promettente, ma va chiarito meglio: serve capire cosa sono e se
non duplicano funzioni gia' coperte da altri dati.

### Tuo punto di vista

I facts hanno senso solo se sono triplette o affermazioni atomiche utili a KG,
conflitti, deprecazioni, validita' temporale e query strutturate. Se duplicano
solo il content, diventano rumore.

### Sistema attuale

Il backend deriva facts dalle memorie. Un fact e' una forma piu' atomica del
tipo: entita' - predicato - valore. Puo' avere validita' temporale, status,
confidence/salience storiche e relazioni di supersede. Alcuni facts rumorosi
sono gia' stati marcati come `rejected_extractor_noise`.

### Fix necessari

- Documentare con esempi semplici cosa sono i facts:
  - "Davide" - "preferisce_risposta" - "sintetica quando stanco";
  - "Protocollo Zero-Luce" - "response_format" - "4 blocchi";
  - "cioccolato" - "vincolo_utente" - "limite personale".
- Validare se facts migliorano davvero KG, conflitti e deprecazioni.
- Spostare estrazione e correzione facts in job di manutenzione robusti.
- Evitare facts generici generati da substring o alias troppo larghi.
- Non consegnare a Scarlet tutti i facts grezzi: includere solo quelli utili
  al pacchetto memoria corrente.

## Memory Surfaces

### Mio punto di vista

Le surfaces sembrano dati derivati da altri dati. Vanno bene se servono al
retrieve, ma non devono creare ridondanza cognitiva o incoerenza. Scarlet deve
ricevere un pacchetto memoria pulito, non tutte le superfici interne.

### Tuo punto di vista

Concordo. Le surfaces non sono verita' nuove: sono indici rebuildable. Sono
giustificate solo se una stessa memoria deve essere ricercabile da prospettive
diverse senza sporcare il content canonico.

### Sistema attuale

Il backend genera superfici come `memory_text`, superfici type-specific,
`future_use_text`, `temporal_text`, `fact_bundle_text`, `conflict_guard_text` e
profili KG. Alcune possono promuovere una memoria nel retrieve, altre sono
solo supporto.

### Fix necessari

- Mantenere surfaces come indici derivati, mai come fonte canonica.
- Non inviare surfaces grezze a Scarlet nel pacchetto normale.
- Inviare al massimo:
  - memoria canonica;
  - motivo sintetico di retrieve;
  - route di retrieve;
  - snippet/evidenza se utile.
- Assicurare che future-use, temporal e lifecycle non selezionino da sole una
  memoria.
- Aggiungere content chunk surfaces per frasi/claim, con deduplica per memoria.
- Prevedere strumenti debug/lab per ispezionare surfaces senza inserirle nel
  contesto user-facing.

## Embedding Vectors

### Mio punto di vista

La triangolazione e' fondamentale: content embedding trova ricordo diretto, KG
trova ricordi vicini, temporalita' restringe, rerank decide cosa conta davvero
per la query corrente.

### Tuo punto di vista

Concordo. Il punto difficile e' scegliere cosa embeddare e con quali ruoli, in
modo che la memoria di Scarlet assomigli al comportamento umano senza
saturare contesto o recuperare ricordi debolmente collegati.

### Sistema attuale

Il backend salva vettori per superfici di memoria. La query viene embeddizzata
al momento del retrieve e confrontata con superfici cacheate. Il ranking ibrido
puo' combinare sparse, dense, rerank, KG e segnali storici.

### Fix necessari

- Definire una policy stabile di embedding:
  - content completo;
  - frasi/claim del content quando utile;
  - facts canonici;
  - nodi KG selezionati;
  - superfici temporali solo come supporto.
- Evitare che superfici ausiliarie promuovano da sole una memoria.
- Rendere il rerank l'arbitro finale della query corrente.
- Misurare su dataset sporco e realistico, non su pochi esempi facili.
- Separare score interni da pacchetto dato a Scarlet.
- Valutare se session chunks vanno embeddati con finestra locale prima/dopo,
  deduplica e merge di chunk adiacenti.

## Knowledge Graph

### Mio punto di vista

Scarlet dovrebbe poter navigare il KG quasi naturalmente quando vuole
ricostruire contesto. Oltre alla sessione sorgente, deve poter vedere memorie
vicine che il retrieve diretto non avrebbe trovato, ma che sono connesse per
dominio, entita', contrasto, temporalita' o lifecycle.

### Tuo punto di vista

Concordo. Il KG ha potenziale enorme, ma va trasformato da segnale interno di
ranking a capacita' navigabile e spiegabile. La criticita' e' evitare che
Scarlet lo navighi sempre o in modo dispersivo.

### Sistema attuale

Il backend costruisce un KG leggero con nodi/edge derivati da memorie, facts,
sessioni e domini. Il KG gia' aiuta il retrieve associativo, ma Scarlet non ha
ancora una vera navigazione autonoma e guidata del grafo.

### Fix necessari

- Progettare endpoint/API di navigazione KG per Scarlet.
- Restituire path spiegabili, non solo liste di nodi.
- Collegare KG a:
  - memoria semanticamente recuperata;
  - sessione sorgente;
  - facts;
  - memorie vicine;
  - deprecazioni e conflitti.
- Aggiornare system prompt solo quando la navigazione KG esiste davvero.
- Definire regole operative:
  - quando basta la memoria;
  - quando aprire sessione sorgente;
  - quando navigare KG;
  - quando fermarsi per non disperdersi.
- Misurare se KG migliora recall human-like su richieste implicite.

## Memory Proposals

### Mio punto di vista

L'architettura proposals sembra buona. La discussione sui job va tenuta per
ultima, cosi' si puo' vedere la lista completa dei processi necessari e capire
quali unire o separare.

### Tuo punto di vista

Concordo. Le proposals sono gia' il punto piu' prudente per non salvare tutto
subito e per recuperare memorie mancate. I job vanno disegnati dopo aver
chiarito quali campi restano canonici e quali diventano derivati.

### Sistema attuale

La manutenzione post-sessione genera proposals, le confronta con memorie
simili, archivia duplicati/scarti e puo' applicare create sicuri o lasciare
pending review.

### Fix necessari

- Tenere proposals come ledger di manutenzione, non come superficie Scarlet.
- Definire piu' avanti la tassonomia job:
  - session review;
  - missed-memory review;
  - proposal resolution;
  - tags/facts/KG enrichment;
  - lifecycle duplicate/update/deprecate;
  - usage review;
  - Dream review futura.
- Decidere quali job possono essere uniti per evitare ridondanza.
- Mantenere archive giornaliero per scarti/duplicati e casi limite.

## Campi senza fix immediato

Questi campi sono considerati corretti o non prioritari in questa discussione:

- `id`: backend-owned, stabile.
- `status`: utile per active/deprecated e lifecycle.
- `created_by`: utile per audit Scarlet vs maintenance.
- `source_session_id`: punto forte del sistema semantic -> episodic.
- `source_turn_id`: utile per localizzazione.
- `source_message_id`: da popolare in futuro, ma non urgente.
- `created_at`, `updated_at`, `last_used_at`: corretti e utili per tempo e
  manutenzione.

## Ordine suggerito di discussione prima del codice

1. Search scope bug: default cross-scope per ricerca manuale.
2. Deprecazione di `confidence` e `salience` come campi model-supplied.
3. Type/scope libero via embedding: esperimento reversibile e metriche.
4. Content multi-vector: memoria intera piu' frasi/claim.
5. Pacchetto memoria model-facing pulito.
6. Enrichment jobs per tags, metadata, facts e KG.
7. Navigazione KG per Scarlet.
8. Revisione completa dei job di manutenzione.
