# Branch: Multi-Agente E Sub-Processi

Last updated: 2026-05-25  
System version assessed: V1.0.1  
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

## Stato attuale

Valutazione: L1.

Non esiste un sistema multi-agente. Esiste solo il primo processo background
deterministico/LLM-assisted per summary e missed-memory review report-only.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Runtime event control plane.
- Idle maintenance worker.
- Decisione: non aggiungere endpoint duplicati per reflection/blackboard.

## Evolutive

- Memory maintainer come processo controllato.
- Source verifier per claim sensibili.
- Proposal reviewer per memorie candidate.
- Planner operativo per task lunghi.
- Subprocessi solo dopo prova che runtime context + singolo agente non bastano.
