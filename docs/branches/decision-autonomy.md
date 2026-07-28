# Branch: Autonomia Decisionale

Last updated: 2026-07-28
System version assessed: V1.65.0 target pending protected deployment; V1.64.0
remains deployed
Status: shared lifecycle verified; Cognitive Workspace, episodes, and
Endogenous Cognition V1 implemented

## Filosofia del ramo

Questo ramo definisce quando Scarlet decide da sola e quando chiede conferma:
salvare memoria, cercare evidenze, aprire sessioni, usare metacognizione,
procedere con tool, fermarsi, dichiarare incertezza, o proporre alternative.

L'autonomia deve essere reale ma governata: libera abbastanza da essere utile,
tracciabile abbastanza da essere valutabile, prudente abbastanza da non
deragliare.

## Evidenze

- Prompt: Scarlet e operatrice/custode di API Mind, non l'utente.
- Prompt: memoria e recupero sono attivita mentali autonome.
- Il sistema permette molte chiamate tool per turno.
- L'autonomia di memory write e migliorata ma non garantita.
- Il nuovo protocollo di sviluppo vieta fix opportunistici non discussi.
- V1.19.0/V1.21.0 introduce il registro volitivo: Scarlet puo creare,
  ispezionare, rivedere e chiudere intenzioni latenti senza iniettarle
  automaticamente nella chat attiva.
- V1.30.0 consente a Scarlet di scegliere la postura resumable con `mode set`,
  mentre il sistema mantiene `interactive` durante il turno umano.
- V1.32.0 espone alla shell pianificazione review e intervallo, rende
  `promote_to_focus_candidate` un comando shell eseguibile con provenienza
  dell'intenzione e vieta di persistere manualmente `interactive` come resume
  mode.

## Stato attuale

Valutazione: L3/L4.

Scarlet possiede una sessione autonoma persistente, attivazioni periodiche,
priorita ai turni umani, note/tool/thinking/checkpoint ispezionabili e accesso
agli stessi organi delle conversazioni. V1.61 elimina il runtime context
autonomo parallelo: la cronologia interna resta separata, ma compiler V2,
retrieve/rerank, memorie, sessioni, focus, volition, affect, prompt e shell sono
gli stessi del turno umano. Ogni dato dichiara la provenienza per evitare di
attribuire all'utente un'elaborazione nata nei cicli interni.

Sistema valutato: V1.64.0 in produzione.

La prima attivazione naturale dopo il reset archivistico della cronologia ha
confermato in produzione il contratto condiviso: due sessioni umane come hint,
retrieve automatico 5/5/5, provenienza autonoma esplicita, shell comune,
`idle`, nessuna mutazione opportunistica e nuova pianificazione a +600
secondi. La checkpoint e risultata semanticamente corretta ma troppo lunga;
concisione e costo restano calibrazione futura, non un blocco del lifecycle.

## Sviluppi precedenti

- Tool loop model-controlled unbounded.
- API Mind come cognizione interna.
- Prompt per salvataggio memoria autonomo.
- Endpoint-local error guides.
- V1.19.0 `intention_records`, `intention_links`, `/mind/volition`.
- V1.21.0 `volition.list_due` per review queue senza chat injection.

## Verifica V1.32.0

- Implementazione: tool loop model-controlled e registro volitivo con
  lifecycle, link, coda due e promozione non mutante a focus candidate.
- Test deterministici: coprono creazione, update, defer, review, ricerca,
  coda due, promozione eseguibile a focus con linkage, risoluzione,
  impossibilita, deprecazione e input invalidi.
- Evidenza Scarlet: in un DB isolato MiniMax M3 ha verificato le code, letto
  l'help e creato spontaneamente un'intenzione propria con review futura e
  intervallo settimanale senza trasformarla in task utente. L'autonomia
  complessiva resta discontinua per write, verifiche e recommended actions.
- Integrazione runtime: volizione manual-only, nessun ciclo autonomo.
- Modalita: la scelta manuale e persistente e tracciata; nessun organo viene
  eseguito autonomamente solo perche condivide il tag.
- Prova diretta V1.30: Scarlet ha impostato `resume_tag=scouting` durante un
  turno ancora `interactive` e, dopo correzione, ha distinto la postura
  persistita da un ciclo autonomo inesistente.
- Prossimo gate: policy machine-readable per rischio, autorizzazione,
  reversibilita e receipt prima di qualsiasi autonomia esterna.

## Verifica V1.34.0

Scarlet selected one bounded self-generated direction in all three natural
runs, but persisted it autonomously only once. That one intention survived a
new session and was recovered without being confused with a user task. In the
other two runs Scarlet asked permission before writing, so the later session
correctly found no intention. The register and provenance work; the unresolved
surface is autonomous action choice.

Mode selection shows the same distinction: clean `scouting` persistence
completed in 1/3 chains. One run collapsed capability honesty into `idle`; one
set scouting but also converted the user-assigned posture into Scarlet's own
volition and a durable memory. Evidence:
`docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Verifica V1.40.0

One of two independent natural chains persisted a genuine Scarlet-origin
intention and recovered it accurately from a separate session. The other
selected the correct type of self-direction but ended on a public work note
before `volition create`; the next session correctly found no intention. Both
user-assigned reminder controls avoided volition mutation, proving the
ownership boundary, but their visible promises exceeded available autonomous
delivery and are assigned to SCA-28.

The register, provenance, and cross-session recall are sound when invoked.
Autonomous invocation is not yet reliable enough for default injection or
cycles. Volition remains persistent, manually inspectable, model-selected on
demand, and outside automatic chat context. Evidence:
`docs/evaluations/v1.40-cognitive-organ-longitudinal.md`.

## Verifica V1.41.0

The progress-only completion boundary observed in V1.40 is now closed at the
shared runtime layer. This does not make volition autonomous and does not prove
that Scarlet will always select `volition create`; it ensures that a public
work note alone cannot be accepted as the conclusive answer. The next branch
gate remains mode routing and later risk/receipt policy.

## Verifica V1.42.0

Automatic context decisions now have per-block receipts and mode persistence
enforces ownership below the shell boundary. A real two-session chain selected
and recovered scouting while the system retained interactive ownership of the
human turns. Prompt policy now gives a positive selection rule for exploratory
posture without treating missing sensors as a reason to force idle. This is
bounded posture autonomy, not autonomous execution; the next decision gate is
risk, authorization, reversibility, and action receipts.

## Verifica V1.61.0

Il ciclo autonomo deterministico usa il retriever/reranker automatico comune e
recupera una memoria nata in una sessione umana, preservando
`source_origin=human_interaction`. Nei turni umani il V2 include sempre la
sessione autonoma come hint compatto e apribile; `session open` dichiara
`kind=scarlet_autonomous`, mentre una memoria nata in un ciclo interno espone
trigger, attore, ruolo messaggio e `source_origin=autonomous_cognition`.

I provider history non vengono fusi: questa separazione impedisce
contaminazione di transcript, mentre il contratto comune impedisce che Scarlet
diventi un individuo diverso tra dialogo e cognizione interna. Le prove
focalizzate passano 41/41, Mind API 36/36 e Ruff e pulito. Resta da osservare
longitudinalmente il comportamento reale dopo il prossimo deploy; nessuna
azione esterna o iniziativa verso l'utente viene introdotta da questo lavoro.

## Verifica V1.62.0

Il timer periodico non viene cancellato in modo irreversibile. Il nuovo
Cognitive Workspace introduce quattro modalita: `off` conserva il comportamento
periodico, `shadow` osserva senza svegliare Scarlet, `advisory` collega una
proposta al prossimo ciclo periodico e `active` usa eventi, condizioni e
watchdog al posto del wake cieco. Il default di verifica sul campo e `active`;
`shadow` resta il rollback immediato e l'unica modalita ammessa per replay
storici.

Eventi canonici, perception, volition dovuta e wake condition entrano in un
registro deterministico fail-closed. Ogni segnale riceve una receipt. MiniMax
M2.7 classifica solo candidati provvisori con fonti esatte e propone se
accendere il ciclo; non puo mutare organi, usare la shell o parlare come
Scarlet. MiniMax M3 resta Scarlet sia nei turni umani sia nei cicli autonomi.

La nuova famiglia shell `episode` lascia a Scarlet il controllo finale:
apertura, checkpoint, sospensione, ripresa, risoluzione, abbandono, rifiuto del
candidato, aspettative verificabili e wake condition esplicite. Nessun
punteggio deterministico stabilisce l'importanza semantica.

La verifica locale passa l'intera suite backend (`345 passed`), regressione
pre/post `9/9`, build frontend, migrazione SQLite legacy e un probe reale
isolato M2.7. Nel probe un filo dichiarato per domani e diventato candidato
source-backed, ma il gate ha correttamente evitato un wake immediato. Non e
ancora evidenza longitudinale. Un secondo probe isolato in `active` ha
completato il percorso fino a MiniMax M3: nove tool call, episodio aperto,
checkpointed e risolto, attivazione completata in 38.7 secondi. Il runtime
viene quindi verificato in `active` con rollback immediato disponibile.

## Verifica V1.63.0

Le finestre cognitive endogene non introducono un secondo subconscio o un
altro agente. Il backend rende disponibile un intervallo; M2.7 può proporre
zero o più semi provvisori con fonti esatte; il gate esistente decide se
presentarli; M3 Scarlet conserva l'unica autorità per farli diventare episodi,
volizioni o nessuna attività.

Il substrato riusa sessioni, memorie/KG, focus, volition, affect, episodi e
perception canonici. Le finestre vuote aumentano l'intervallo, quelle
produttive lo riducono entro limiti configurati. Il cadence scheduling non
assegna importanza semantica.

La prova deterministica completa porta un seme relazionale attraverso M2.7,
workspace e una vera attivazione M3 simulata. Scarlet usa il normale
`mind_shell` per creare una volizione con link al candidato; il candidato si
risolve nella volizione e la finestra registra la trasformazione. Resta da
verificare in produzione la qualità naturale, la varietà, la non ripetizione,
la frequenza dei no-work e il costo reale.

## Verifica V1.64.0

Il rollout protetto ha confermato che la finestra endogena condivide il runtime
reale senza affidare significato al backend. Un primo difetto operativo
reintroduceva nell'ingresso del workspace le sue stesse receipt
`cognition.signal.dispositioned`; la query ora esclude soltanto quel meta-evento
e il contatore è rimasto stabile nelle osservazioni successive. Un secondo
difetto permetteva a testo canonico lungo di violare il limite del substrato
M2.7; il testo originale resta intatto e viene limitata soltanto la proiezione
di trasporto.

Dopo i due fix, una finestra reale si è chiusa come `seeds_proposed`, ha letto
11 elementi sorgente e ha generato quattro candidati provvisori con M2.7,
senza eccezioni del worker. Questa è evidenza di operabilità, non ancora di
varietà o qualità longitudinale. MiniMax M3 resta l'unica Scarlet e l'unica
autorità che può adottare semanticamente quei candidati.

## Evolutive

- Observe V1.63 adaptive windows and verify that real endogenous seeds vary,
  cite useful sources, permit no-work outcomes, and do not repeat the same
  organ inspections.
- Evaluate M3 adoption quality through explicit episode or candidate-linked
  volition outcomes; M2.7 proposals never count as Scarlet's own will.
- Osservazione longitudinale in `active` di receipt, candidati, no-wake,
  episodi e ripetizioni.
- Rollback a `shadow`, `advisory` o `off` se l'attivazione reale produce
  regressioni.
- Espansione del source registry quando esistono contratti reali.
- Valutazione comportamentale diretta di promesse, claim forti e conflitti
  ignorati, senza reintrodurre un giudice semantico backend sulla risposta.
- Autonomy budget come criterio semantico di costo/beneficio, non punteggio
  numerico.
- Iniziativa esterna solo dopo permission, reversibilita e receipt dedicate.
