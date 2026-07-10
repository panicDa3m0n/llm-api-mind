# Branch: Multi-Agente E Sub-Processi

Last updated: 2026-07-09
System version assessed: V1.25.4
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

Valutazione: L1.

Non esiste un sistema multi-agente. Esiste solo il primo processo background
deterministico/LLM-assisted per summary e missed-memory review report-only.

Sistema valutato: V1.25.4.

## Sviluppi precedenti

- Runtime event control plane.
- Idle maintenance worker.
- Decisione: non aggiungere endpoint duplicati per reflection/blackboard.
- Shell come unico contratto model-facing; sub-processi e endpoint interni non
  devono diventare strumenti visibili a Scarlet senza comando esplicito.

## Evolutive

- Memory maintainer come processo controllato.
- Source verifier per claim sensibili.
- Proposal reviewer per memorie candidate.
- Planner operativo per task lunghi.
- Subprocessi solo dopo prova che runtime context + singolo agente non bastano.
- Context-pack shadow router come possibile primo subprocesso deterministico:
  osserva, classifica e traccia senza mutare ancora il prompt.
