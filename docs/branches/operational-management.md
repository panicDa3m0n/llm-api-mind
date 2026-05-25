# Branch: Gestione Operativa

Last updated: 2026-05-25  
System version assessed: V1.0.1  
Status: early branch

## Filosofia del ramo

Questo ramo riguarda goal, focus, task, open loops, priorita, piani, stato
operativo e comportamento persistente orientato all'azione.

L'effetto desiderato e che Scarlet non risponda solo turno per turno, ma sappia
gestire lavori nel tempo: ricordare cosa e aperto, decidere il prossimo passo,
separare task attivi da idee future, e mantenere il filo operativo.

## Evidenze

- `scarlet_state` espone focus, goal, mood operativo e open loops come blocco
  backend-seeded.
- Runtime events rendono ispezionabili le attivita svolte.
- Non esiste ancora un vero task manager o goal store modificabile da Scarlet.

## Stato attuale

Valutazione: L2.

Il ramo e avviato come superficie di contesto, ma non ha ancora funzioni
operative reali. `scarlet_state` e utile come seme, non come gestione task
persistente.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Runtime context stratificato.
- `scarlet_state` con focus e open loops.
- Event spine per turni e azioni.
- Idle maintenance come primo processo backend-owned.

## Evolutive

- Goal store persistente.
- Task manager interno con stato: planned, active, blocked, done, abandoned.
- API per aggiornare focus e open loops.
- Collegare task a sessioni, memorie, decisioni e prove.
- Dashboard per goal/focus/task e continuita tra sessioni.
