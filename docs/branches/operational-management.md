# Branch: Gestione Operativa

Last updated: 2026-07-28
System version assessed: V1.65.0 target pending protected deployment
Status: focus, mode routing, and autonomous activation substrate implemented

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
- V1.65 conserva l'activation ledger, la cronologia privata, il defer/yield a
  priorita umana e la provenienza autonoma come confini dell'adapter, ma usa il
  medesimo kernel del turno umano per V2, retrieval, shell, accounting,
  `end_turn`, persistenza e compattazione. Non esiste piu una seconda
  implementazione operativa di questi passaggi.

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

## Verifica V1.40.0

Two independent natural same-session chains created one bounded focus and
resolved the same state on explicit closure: 4/4 technical turns passed. Two
independent casual-topic controls stayed direct and created no focus, volition,
or mode state. Visible state claims agreed with persistence, although creation
answers were sometimes more expansive than the user needed.

Focus is therefore a validated controlled lifecycle, not an instruction to
persist every conversational topic. It remains model-facing only when active;
automatic focus selection and coupling to volition or modes are not accepted.
Evidence: `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`.

## Verifica V1.42.0

Mode routing now emits one ordered receipt per automatic context block, with
capability tags, eligibility, actual delivery, and reason. Off, shadow, and
active policies no longer conflate a tag mismatch with exclusion; unknown
blocks remain fail-open and visible. Native and GPT human turns produce the
same interactive routing boundary, while on-demand shell cognition remains
available independently.

A bounded natural two-session chain persisted `scouting`, recovered it in a
new session, and kept both human turns `interactive`. The first pre-fix probe
had collapsed capability honesty into `idle`; the policy now explicitly
distinguishes idle absence of direction from scouting exploratory orientation.
No idle/scouting autonomous cycle or sensor behavior exists or was claimed.
Evidence: `docs/evaluations/v1.42-agent-mode-routing.md`.

## Aggiornamento V1.60.0

Una sessione interna esclusiva ora ospita cicli autonomi periodici in
`idle|scouting`, senza inventare messaggi umani e senza riusare i job di
maintenance. Il contesto include focus, volition aperte/due, affect e ganci
episodici/mnemonici; Scarlet puo usare la shell e lascia note e checkpoint
persistenti. La UI rende questa cronologia rileggibile.

Questa integrazione non trasforma automaticamente una volition in task, non
seleziona il focus in modo deterministico e non concede sensori o azioni
esterne. L'efficacia della scelta autonoma resta da valutare con cicli reali
isolati.

## Evolutive

- Goal store persistente.
- Task manager interno con stato: planned, active, blocked, done, abandoned.
- API per goal/task/open loops, mantenendo `/mind/focus` come organo separato.
- Collegare task a sessioni, memorie, decisioni e prove.
- Dashboard per goal/focus/task e continuita tra sessioni.
- Valutare una prima implementazione solo dopo approvazione teorica, con
  storage piccolo, eventi obbligatori e nessuna generazione massiva di task.
