# Branch: Metacognizione

Last updated: 2026-06-23
System version assessed: V1.16.0
Status: prototype branch with thinking retrospection and shadow context

## Filosofia del ramo

La metacognizione deve permettere a Scarlet di ragionare sul proprio
ragionamento: verificare assunzioni, criticare bozze, cercare evidenze
mancanti, riconoscere conflitti, decidere se continuare a pensare o rispondere.

Non deve essere fittizia, decorativa o composta da endpoint duplicati. Il ramo
deve puntare a vera utilita nel risultato finale.

## Evidenze

- Esiste un unico endpoint LLM-backed:
  `POST /mind/metacognition/step`.
- Il prompt indica quando usarlo per task complessi, sensibili o incerti.
- Le route parallele di reflection/blackboard/validation sono state rimosse
  per evitare caos.
- Evidenza live ancora insufficiente: Scarlet non invoca sempre la
  metacognizione quando dovrebbe.
- V1.5.0 aggiunge `docs/theory-metacognition.md` per separare
  metacognizione, cognition normale, public notes, maintenance e futuri
  validators prima di introdurre nuova architettura.
- V1.8.0 trasforma l'endpoint esistente in una superficie sperimentale per
  retrospezione del thinking precedente, senza creare endpoint paralleli. Il
  thinking viene trattato come evidenza di processo, non come prova fattuale.
- V1.9.0 introduce `metacognitive.context` come fase shadow: il backend genera
  lezioni candidate e le mostra a evaluator/UI, ma non le passa al modello in
  modalita default.
- I test prompt-pack hanno suggerito che un contesto metacognitivo piccolo e
  mirato puo aiutare, mentre blocchi grandi o generici peggiorano M3.
- V1.16.0 chiarisce nel prompt che la metacognizione e un ciclo operativo
  monitor/choose/act/observe/adapt e che le lezioni riutilizzabili sul proprio
  funzionamento possono diventare memoria semantica metacognitiva.

## Stato attuale

Valutazione: L3.

Tecnicamente implementata come prototipo tracciabile. Il percorso resta unico:
`POST /mind/metacognition/step`. V1.8.0 aggiunge modalita retrospettive che
permettono a Scarlet di richiedere un pacchetto controllato del turno completato
precedente: messaggio utente, risposta finale, note pubbliche, tool call, eventi
e blocchi provider `thinking` con dettaglio `digest`, `excerpt` o `raw`.

La funzione non e ancora validata come comportamento autonomo stabile. Deve
essere testata in conversazioni reali per capire se aiuta Scarlet a recuperare
open loop, spiegare tool choice, riconoscere drift tra pensiero e risposta, e
trovare candidati memoria mancati.

V1.9.0 aggiunge una superficie di osservazione pre-modello:
`metacognitive.context`. In `shadow` mode resta fuori dal prompt e serve solo a
vedere quali lezioni sarebbero state selezionate. In `inject` mode puo entrare
in `runtime_context.blocks` per test A/B controllati.

Aggiornamento V1.16.0: il ramo resta prompt-led per questa slice. Non sono
stati aggiunti endpoint o trigger automatici; il cambiamento e la postura
operativa con cui Scarlet deve osservare e correggere il proprio lavoro.

Sistema valutato: V1.16.0.

## Sviluppi precedenti

- Rimozione della metacognizione visiva fittizia.
- Introduzione delle public work notes.
- Unificazione su `/mind/metacognition/step`.
- Scripted test per schema, alias e JSON repair.
- V1.5.0 teoria Metacognition per owner review.
- V1.8.0 thinking retrospection:
  - nuove modalita `review_previous_turn`, `detect_reasoning_drift`,
    `explain_tool_choice`, `recover_open_loops`,
    `compare_answer_to_reasoning`, `extract_reasoning_digest`,
    `memory_from_reasoning`;
  - `turn_scope="previous"` e `detail="digest|excerpt|raw"`;
  - test backend sul recupero del thinking provider dal turno precedente.
- V1.9.0 metacognitive context shadow:
  - trace `metacognitive.context`;
  - evento `metacognitive.context.shadowed`;
  - stream/UI block `metacognitive_context`;
  - modalita controllata `inject` per inserire il blocco nel runtime context.
- V1.16.0 prompt checkpoint:
  - self-monitoring operativo piu esplicito;
  - loop monitor/choose/act/observe/adapt;
  - possibilita di salvare lezioni metacognitive compatte e sourceable.

## Evolutive

- Prompt reviewer per modalita: verifica fonti, conflitti memoria, decisione
  progettuale, risposta emotiva, task tecnico.
- Continuation loop quando `should_continue=true`.
- Tracce di miglioramento: confronto risposta pre/post metacognizione.
- Trigger automatici basati su rischio, incertezza, conflitto o claim forte.
- Checkpoint metacognitivo unico prima della risposta finale, da valutare dopo
  approvazione teorica e nuovi test comportamentali.
- Esperimenti su uso proattivo:
  - Scarlet recupera un open loop lasciato nel thinking precedente;
  - Scarlet spiega un tool call senza inventare ragioni post-hoc;
  - Scarlet identifica una memoria candidata emersa nel ragionamento ma non
    salvata;
  - Scarlet confronta risposta finale e reasoning per ridurre drift.
- Valutare se una futura metacognizione avanzata debba poter leggere piu turni,
  ma solo dopo evidenza che il singolo-turno precedente porta benefici reali.
- Progettare retrieval chirurgico di lezioni metacognitive solo dopo confronto
  shadow/inject. Metriche minime: overthinking, tool call ridondanti, memoria
  promessa ma non salvata, source claims non verificati, latenza e token.
- Valutare se le lezioni metacognitive salvate da Scarlet vengono recuperate al
  momento giusto o se serve un retrieve separato, chirurgico e non rumoroso.
