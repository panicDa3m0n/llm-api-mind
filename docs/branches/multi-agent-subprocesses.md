# Branch: Multi-Agente E Sub-Processi

Last updated: 2026-07-18
System version assessed: V1.50.0 candidate
Status: planned branch

## Filosofia del ramo

Questo ramo riguarda eventuali processi interni multipli: reviewer,
manutentori memoria, controllori, planner, worker specializzati, processi
background e agenti ausiliari.

Deve evitare caos. Ogni sub-processo deve avere scopo chiaro, trigger chiaro,
tracce, output verificabile e non duplicare funzioni gia coperte dal workflow
agentico principale.

## Evidenze

- Il progetto ha gia rifiutato molti endpoint cognitivi paralleli per evitare
  confusione.
- Esiste idle maintenance backend-owned, ma non e un agente autonomo.
- Runtime events sono un buon substrato per sub-processi futuri.
- V1.26.0 planning apre la strada a un router context-pack in shadow mode:
  deterministico prima, eventualmente assistito da processi interni solo dopo
  evidenza che il routing semplice non basta.

## Stato attuale

Valutazione: L1/L2.

Non esiste un sistema multi-agente. Esiste solo il primo processo background
deterministico/LLM-assisted per summary e missed-memory review report-only.

V1.49.0 rende espliciti i confini interni senza cambiare questa classificazione:
un unico scheduler/worker governa i job, mentre summary/history e memory review
hanno owner separati. Il resolver LLM resta una fase bounded del processo
backend, non una seconda identita agentica o un tool model-facing.

Sistema valutato: V1.50.0 candidate.

## Sviluppi precedenti

- Runtime event control plane.
- Idle maintenance worker.
- Decisione: non aggiungere endpoint duplicati per reflection/blackboard.
- Shell come unico contratto model-facing; sub-processi e endpoint interni non
  devono diventare strumenti visibili a Scarlet senza comando esplicito.

## Verifica V1.29.1

- Implementazione: worker maintenance con fasi deterministiche e resolver LLM
  opzionale; non e un sistema multi-agente.
- Test deterministici: coprono scheduling, supersession, summary, proposal e
  risoluzione cauta.
- Evidenza Scarlet: il risultato puo influire sui turni futuri tramite memoria,
  ma non esiste coordinamento fra agenti.
- Integrazione runtime: background-only; job e proposal non sono contesto
  automatico ne shell model-facing.
- Prossimo gate: misurare limiti del singolo agente e definire contratti
  bounded per reviewer/worker prima di introdurre identita o conversazioni
  multi-agente.

## Verifica V1.49.0

- Implementazione: scheduler, summary/history e memory review sono separati
  dietro un unico facade e un unico lifecycle persistito dei job.
- Test deterministici: frozen pre/post 9/9, focused 32/32, backend 247/247.
- Evidenza diretta: compaction idempotente e source-anchored; un idle job reale
  ha prodotto una summary fedele e nessuna memoria per un dettaglio transitorio.
- Giudizio: la correttezza semantica e stata verificata leggendo output,
  rationale, eventi e record, non dedotta dallo stato `completed`.

## Evolutive

- Memory maintainer come processo controllato.
- Source verifier per claim sensibili.
- Proposal reviewer per memorie candidate.
- Planner operativo per task lunghi.
- Subprocessi solo dopo prova che runtime context + singolo agente non bastano.
- Context-pack shadow router come possibile primo subprocesso deterministico:
  osserva, classifica e traccia senza mutare ancora il prompt.
