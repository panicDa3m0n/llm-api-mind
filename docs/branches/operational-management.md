# Branch: Gestione Operativa

Last updated: 2026-07-14
System version assessed: V1.34.0
Status: focus shell verified; natural lifecycle remains variable

## Filosofia del ramo

Questo ramo riguarda goal, focus, task, open loops, priorita, piani, stato
operativo e comportamento persistente orientato all'azione.

L'effetto desiderato e che Scarlet non risponda solo turno per turno, ma sappia
gestire lavori nel tempo: ricordare cosa e aperto, decidere il prossimo passo,
separare task attivi da idee future, e mantenere il filo operativo.

## Evidenze

- `scarlet_state` espone focus, goal, mood operativo e open loops come blocco
  backend-seeded, ma `focus_context` supersede il focus legacy quando attivo.
- Runtime events rendono ispezionabili le attivita svolte.
- Non esiste ancora un vero task manager o goal store modificabile da Scarlet.
- V1.5.0 aggiunge `docs/theory-goal-focus-task.md` per definire cosa devono
  significare goal, focus, open loops e task in un individuo digitale, prima di
  introdurre API o storage operativi.
- V1.18.0/V1.21.0 implementa il primo organo focus: storage, lifecycle,
  runtime block e timeline di transizione.
- V1.30.0 aggiunge la modalita agentica come postura operativa separata dal
  focus: `interactive` e una condizione di turno, non l'oggetto attentivo.
- V1.32.0 corregge `focus hold` affinche persista davvero `status=held`, rende
  esplicita la paginazione di list/search/timeline e restituisce
  `focus.not_found` per letture mirate inesistenti.

## Stato attuale

Valutazione: L2/L3.

Il ramo ha una prima funzione operativa reale nel focus: `POST /mind/focus`
permette set/update/hold/shift/defer/resolve/impossible/read/list/search e
V1.21.0 aggiunge `timeline` per ispezionare gli spostamenti attentivi.
Goal, task e open loops restano ancora teorici/progettuali.

Sistema valutato: V1.32.0.

## Sviluppi precedenti

- Runtime context stratificato.
- `scarlet_state` con focus e open loops.
- Event spine per turni e azioni.
- Idle maintenance come primo processo backend-owned.
- V1.5.0 teoria Goal/Focus/Task per owner review.
- V1.18.0 focus records/transitions, `/mind/focus`, `focus_context`.
- V1.21.0 `focus.timeline` per chiudere l'ispezione storica standalone.

## Verifica V1.32.0

- Implementazione: focus persistente e tracciato; maintenance jobs gestiscono
  lavoro backend, non task di Scarlet.
- Test deterministici: coprono lifecycle focus, stato held persistito,
  transizioni, timeline paginata, ricerca e not-found mirato.
- Evidenza Scarlet: in un DB isolato MiniMax M3 ha letto l'assenza di focus,
  consultato `help focus`, impostato un focus coerente col vincolo umano e
  recuperato correttamente da un successivo comando memoria malformato. Resta
  assente una prova longitudinale di mantenimento autonomo del focus.
- Integrazione runtime: `organ_focus_mode=off` di default; goal/task/open
  loop restano non implementati.
- Modalita: registry e shell `mode` sono implementati, ma non sostituiscono
  focus, goal o task e non rappresentano processi background.
- Prossimo gate: approvare teoria goal-focus-task, definire ownership e
  lifecycle minimi, poi collegare il focus senza trasformarlo in filtro
  memoria.

## Verifica V1.34.0

Three independent two-turn focus chains show that storage is not the limiting
surface: focus creation used the dedicated organ only 1/3, and explicit
resolution passed 0/3. In two chains Scarlet substituted semantic memory for
foreground state; in the third she read the active focus but interpreted
“consideralo concluso” as setup completion and left it active. Natural focus
lifecycle must be calibrated before goal/task expansion.

The separate mode chain preserved a clean `scouting` posture across a new
session in 1/3 repetitions while keeping active human turns `interactive`.
Another run reached scouting but duplicated the user directive into memory and
volition, so its organ boundaries failed even though mode persistence worked.
Evidence: `docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Evolutive

- Goal store persistente.
- Task manager interno con stato: planned, active, blocked, done, abandoned.
- API per goal/task/open loops, mantenendo `/mind/focus` come organo separato.
- Collegare task a sessioni, memorie, decisioni e prove.
- Dashboard per goal/focus/task e continuita tra sessioni.
- Valutare una prima implementazione solo dopo approvazione teorica, con
  storage piccolo, eventi obbligatori e nessuna generazione massiva di task.
