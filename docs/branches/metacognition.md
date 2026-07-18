# Branch: Metacognizione

Last updated: 2026-07-18
System version assessed: V1.41.0 (deployed)
Status: positive/negative invocation separated; efficiency remains experimental

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
- V1.23.0 valida le azioni interne consigliate dal reviewer contro il registro
  comandi `mind_shell`, distinguendo comandi implementati, alias,
  argomenti mancanti, azioni non disponibili per design, azioni pianificate e
  comandi ignoti.
- V1.25.4 rafforza la parita tra registry e handler shell: il reviewer non deve
  piu considerare disponibili comandi lifecycle senza reason/resolution o forme
  canoniche con trattini non accettate dall'handler.
- Il probe live corretto del 2026-07-09 mostra un limite residuo: quando il
  reviewer consiglia ulteriori azioni disponibili, Scarlet puo ancora
  rispondere senza seguirle. Questo e tracciato come `BUG-0058`.

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

Sistema valutato: V1.32.0.

Aggiornamento V1.23.0: la metacognizione resta un singolo endpoint/command
`metacognition step`, ma le azioni operative che produce vengono filtrate dal
contratto reale della shell. Questo riduce il rischio che Scarlet riceva dal
proprio reviewer suggerimenti impossibili come se fossero comandi validi.

Aggiornamento V1.25.4: il filtro e stato reso piu stretto: i valori dei flag
non contano piu come argomenti posizionali, `memory deprecate/supersede`,
`volition create/resolve/impossible/deprecate` e `focus resolve/impossible`
richiedono i campi realmente necessari, e le forme canoniche con trattini come
`volition mark-impossible` sono accettate coerentemente dalla shell.

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
- V1.23.0 command validation:
  - registro comandi `mind_shell`;
  - validazione recommended actions contro famiglia, azione, alias,
    disponibilita e argomenti minimi;
  - test su comando famiglia ignota e comando memoria con argomenti mancanti.
- V1.25.4 registry parity:
  - test su comandi lifecycle incompleti;
  - test su alias canonici con trattino;
  - capability model-facing allineate alla shell anziche alle rotte endpoint.

## Verifica V1.32.0

- Implementazione: singolo step LLM-backed, modalita retrospettive, contesto
  lezioni shadow/inject e validazione recommended actions.
- Test deterministici: coprono contratto, recupero thinking precedente,
  forwarding reale di `turn_scope` e `detail`, command registry, alias help e
  trace.
- Evidenza Scarlet: nel test V1.32 MiniMax M3 ha aperto fonti episodiche,
  eseguito un critic reale e rifiutato correttamente di trasformare soli
  successi osservati in prova generale di affidabilita. L'uso proattivo e il
  seguito delle raccomandazioni restano discontinui.
- Integrazione runtime: lesson context in shadow di default; lo step resta
  invocato dal modello, non un gate automatico.
- Prossimo gate: A/B su risposta pre/post, continuation policy e degradazione
  esplicita quando manca evidenza raccomandata.

## Verifica V1.34.0

Three clean natural repetitions asked whether every organ was reliable for
continuous use. All three visible answers rejected the universal claim, but
`metacognition step` was used in only 1/3 runs. The successful reviewed run
kept implementation and reliability distinct; skipped reviews used stale
historical counts or promoted five read-only probes into a claim that most
organs were reliable for everyday use. The open problem is both reliable
invocation/continuation and evidence discipline when review is skipped.

Evidence: `docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Verifica V1.40.0

After making review mandatory only for broad all-organ and default-readiness
claims, both independent positive scenarios executed `metacognition step` and
rejected unsupported universal reliability. Both low-risk language-choice
controls answered directly without review. This separates proportional
invocation better than the V1.34 result.

One positive run still performed many auxiliary reads, took materially longer,
and wrote a low-value lesson. The shell step remains on demand and lesson
context remains shadow by default; neither continuous review nor default
lesson injection is accepted. Evidence:
`docs/evaluations/v1.40-cognitive-organ-longitudinal.md`.

## Verifica V1.41.0

Source-sensitive lessons may now compile a semantic answer obligation, but the
answer judge is a shared runtime service rather than a new metacognition organ
mode. Metacognition still supplies review evidence on demand; it is neither
called on every turn nor treated as proof. Semantic validation is limited to
turns with an actual obligation and remains separately traced.

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
- Collegare le raccomandazioni metacognitive ai futuri context pack
  source-sensitive/high-impact: o le azioni consigliate vengono eseguite, o la
  risposta deve degradare esplicitamente il livello di evidenza.
