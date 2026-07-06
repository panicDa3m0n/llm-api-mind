# Branch: Emotivita Computazionale

Last updated: 2026-06-26
System version assessed: V1.21.0
Status: first affective organ standalone surface closed

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
- appraisal deterministico su messaggio utente, memory context, eventi recenti
  e precedente stato affettivo;
- variabili numeriche interne con inerzia/decadimento semplice;
- composizione in emozione umana (`curiosity`, `tenderness`, `frustration`,
  `caution`, `relief`, `enthusiasm`, `sadness`);
- persistenza in `affect_states`;
- blocco compatto `affective_context` in modalita `model`;
- modalita `shadow` per calibrazione senza iniezione al modello.
- endpoint read-only `/mind/affect` con azioni `read`, `list`, `prototypes`.

Sistema valutato: V1.21.0.

Limite principale: i prototipi sono reali e tracciabili ma ancora primitivi;
non sono stati calibrati su lunghe sessioni live con Scarlet.

## Sviluppi precedenti

- Identita conversazionale.
- Salience sulle memorie.
- `scarlet_state.mood_expression`.
- Preferenze utente su stile/energia comunicativa.
- V1.20.0: primo core affettivo persistente, traceable, e model-facing dietro
  flag.
- V1.21.0: endpoint read-only per ispezione affettiva e prototipi.

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
