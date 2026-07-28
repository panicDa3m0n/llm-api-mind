# Branch: Emotivita Computazionale

Last updated: 2026-07-28
System version assessed: V1.65.0 target pending protected deployment; V1.64.0
remains deployed
Status: structural appraisal retained; semantic affect appraisal requires redesign

## Filosofia del ramo

Questo ramo riguarda stati affettivi computazionali human-like: emozioni
apprese dal sistema tramite osservazioni reali e rese a Scarlet come stato
interno proprio, non come semplice stile di risposta.

L'obiettivo non e fare sentiment analysis o styling emotivo. L'obiettivo e
generare uno stato emotivo backend-appraised che, quando esposto a Scarlet,
modifica il comportamento del modello: postura, cautela, calore, curiosita,
energia, delicatezza e modo di rispondere.

Decisione V1.20.0: l'affetto influenza il modello, non il backend. Non deve
modificare automaticamente retrieval, focus, intenzioni, scrittura memorie,
soglie operative o job autonomi.

## Evidenze

- `scarlet_state` contiene ancora `mood_expression` come fallback legacy, ma
  `affective_context` lo supersede quando presente.
- Le memorie personali possono avere salienza, ma non ancora pesi emotivi veri.
- Il prompt valorizza presenza, calore e attenzione senza eccessi.
- V1.20.0 introduce `affect_states`, `organ.affect` traces, eventi
  `organ.affect.appraised` / `organ.affect.surfaced`, e runtime block
  `affective_context` dietro `organ_affect_mode`.
- Il confine model-only e tracciato sia nel pack sia negli eventi.
- V1.21.0 aggiunge `POST /mind/affect`, read-only, per leggere stato,
  storico e prototipi senza permettere a Scarlet di mutare emozioni via tool.

## Stato attuale

Valutazione: L3.

Il ramo ha ora un primo core implementato:

- prototipi emozionali umani versionati in `backend/app/mind/affect.py`;
- appraisal deterministico solo su eventi runtime osservabili, memory negative
  evidence e precedente stato affettivo;
- variabili numeriche interne con inerzia/decadimento semplice;
- composizione in emozione umana (`curiosity`, `tenderness`, `frustration`,
  `caution`, `relief`, `enthusiasm`, `sadness`);
- persistenza in `affect_states`;
- blocco compatto `affective_context` in modalita `model`;
- modalita `shadow` per calibrazione senza iniezione al modello.
- endpoint read-only `/mind/affect` con azioni `read`, `list`, `prototypes`.

Sistema valutato: V1.32.0.

Limite principale: i prototipi sono reali e tracciabili ma ancora primitivi;
non sono stati calibrati su lunghe sessioni live con Scarlet.

Correzione V1.64: il backend non interpreta piu parole, punteggiatura o frasi
del messaggio come emozioni. Un futuro appraiser semantico dovra essere
model-backed, sourceable, incerto e non autorizzato a cambiare altri organi.

## Sviluppi precedenti

- Identita conversazionale.
- Salience sulle memorie.
- `scarlet_state.mood_expression`.
- Preferenze utente su stile/energia comunicativa.
- V1.20.0: primo core affettivo persistente, traceable, e model-facing dietro
  flag.
- V1.21.0: endpoint read-only per ispezione affettiva e prototipi.

## Verifica V1.32.0

- Implementazione: completa come primo organo standalone (appraisal,
  persistenza, trace/eventi, shell read-only, blocco opzionale).
- Test deterministici: coprono shadow/model, neutralita, eventi recenti,
  filtri emotion/mode/status, paginazione, not-found e prototipi.
- Evidenza Scarlet: in un DB isolato MiniMax M3 ha usato `affect read` e
  `affect prototypes`, ha riportato il solo stato realmente registrato e ha
  distinto affect autorevole da mood legacy. Calibrazione relazionale
  multi-sessione ancora insufficiente.
- Integrazione runtime: `organ_affect_mode=off` di default; quindi
  implementato non significa normalmente attivo.
- Prossimo gate: A/B shadow/model su sessioni lunghe prima di collegare affetto
  a memoria, focus, volizione o decisioni.

## Verifica V1.34.0

The first repeated paired natural scenario exposed BUG-0082. An explicit
exasperation message produced `organ.affect` traces in 3/3 runs, but only the
fragment `blocc` contributed to `frustration=0.26`; no prototype exceeded the
activation threshold, no row was persisted, and no `affective_context` reached
Scarlet. Some visible answers still regulated tone well, confirming that
language-model empathy and the external affect organ must be evaluated
separately.

Do not tune one keyword or threshold from this single phrase. SCA-4 must add
varied emotional positives, neutral controls, and paired transitions before a
prototype change. Evidence:
`docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Verifica V1.40.0

SCA-4 isolated the failed recovery transition: resolution wording still
contained the obstruction substring and full prior frustration carry
overwhelmed relief. Explicit resolution now suppresses contradictory current
frustration evidence, attenuates only prior-frustration carry, and emits a
traceable relief cause.

Two model chains, two shadow chains, and two neutral controls passed all ten
post-fix technical contracts. Model and shadow answers were both broadly
appropriate, and model mode did not yet demonstrate a clear qualitative
advantage. The default therefore remains `shadow`; `model` is restricted to
controlled experiments and affect still cannot mutate another organ.
Evidence: `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`.

## Evolutive

- Emotional salience sulle memorie.
- Calibrazione dei prototipi su test A/B `shadow` vs `model`.
- Event-based affect updates durante loop agentici lunghi, senza mutare altri
  organi.
- Eventuale classifier/embedding prototype matching se i prototipi
  deterministici risultano troppo fragili.
- Affettivita persistente piu ricca: episodi, decadimento piu realistico,
  saturazione, ritorni emotivi, e collegamenti auditabili a sessioni/memorie.
- Studio futuro, solo se supportato da evidenze, di eventuali pressioni leggere
  su altri organi. Non implementare finche il confine model-only non e ben
  valutato.
