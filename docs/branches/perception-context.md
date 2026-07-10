# Branch: Percezione E Contesto

Last updated: 2026-07-09
System version assessed: V1.25.4
Status: active branch

## Filosofia del ramo

Questo ramo definisce cosa Scarlet percepisce prima di rispondere: tempo,
lingua, profilo, luogo operativo, sessione, messaggio corrente, memoria
automatica, eventi recenti, capability API Mind e stato dinamico.

L'effetto desiderato e trasformare il contesto backend in percezione operativa:
Scarlet non deve indovinare il mondo, deve ricevere blocchi affidabili e
stratificati.

## Evidenze

- Ogni turno costruisce `memory.context` e `runtime.context` prima della
  richiesta LLM.
- `runtime.context` contiene `session_context`, `message_context` e
  `scarlet_state`.
- Prove live confermano che Scarlet legge ora, lingua, blocchi, sessioni
  precedenti e profilo direttamente dal runtime context.
- Il runtime espone una sola fonte temporale valida: `temporal_context.now`.
- `message_context.world.location` espone locale configurato Italia/Europe-Rome
  come evidenza di paese/fuso, non GPS.
- `docs/block-registry.md` mappa ora i blocchi model-facing, i mirror
  compatibili, gli eventi trace-only e il rendering UI, cosi le future
  ottimizzazioni del context possono partire da evidenza reale.
- La UI espone un inspector `Modello` che mostra il `runtime_context` effettivo
  inviato a MiniMax e segnala i mirror top-level ridondanti rispetto ai blocchi
  canonici.
- V1.7.0 assegna identita e lifecycle ai blocchi stream UI, cosi la percezione
  visibile durante il turno resta collegata agli eventi persistiti.
- V1.7.1 chiarisce nel prompt che i blocchi gia presenti nel turno possono
  bastare per risposte contestuali: Scarlet non deve richiamare API Mind solo
  per confermare dati gia forniti dal runtime context o dalla memoria
  selezionata.
- V1.9.0 aggiunge una superficie shadow separata,
  `metacognitive.context`, visibile in trace/UI ma non model-facing in modalita
  default. In modalita controllata `inject` puo diventare un blocco
  `metacognitive_context` dentro `runtime_context.blocks`.
- V1.23.0 riduce rumore nel blocco automatico memoria: i conflitti
  model-facing derivano solo da facts atomici divergenti, non da semplice
  overlap di tag/token tra memorie selezionate.
- V1.25.4 allinea `message_context.api_mind.capabilities` e il mirror
  top-level `capabilities` al contratto model-facing `mind_shell`, separando
  le rotte endpoint interne/debug/manutenzione dalle vere capacita cognitive
  presentate a Scarlet.
- V1.26.0 planning introduce `docs/runtime-context-packs.md` come baseline per
  classificare organi, fonti e capacita in spine sempre attiva, pack
  condizionali, operazioni on-demand e manutenzione background-only.

## Stato attuale

Valutazione: L4.

Il ramo e uno dei piu solidi. Il modello riceve blocchi chiari, tracciati e
renderizzati in UI. V1.6.0 rende anche ispezionabile l'input model-facing
completo, separando blocchi canonici e campi compatibili ridondanti. La
percezione non e ancora completa perche mancano ambiente esterno reale,
device/app state avanzato, profilo multiutente e stato Scarlet modificabile
tramite API.

Sistema valutato: V1.25.4.
Aggiornamento V1.7.1: la percezione viene ora usata anche per calibrare lo
sforzo. Se il runtime context, la memoria selezionata o la history visibile
contengono gia l'evidenza sufficiente, il prompt istruisce Scarlet a non
duplicare la verifica con chiamate rituali.

Aggiornamento V1.9.0: il ramo supporta osservabilita shadow per lezioni
metacognitive senza cambiare il contesto model-facing normale.

Aggiornamento V1.23.0: `runtime_context.memory_context.conflicts` non segnala
piu' related overlap come conflitto. Questo mantiene il contesto automatico piu
pulito e impedisce che cautela/affect/debug vengano attivati da somiglianze
generiche tra memorie.

Aggiornamento V1.25.4: la percezione delle capability non deriva piu
direttamente da `MIND_API_ROUTES`. Il modello vede `interface=mind_shell`,
famiglie comando e status da registry; endpoint come
`memory.facts.backfill` restano indicati solo come
`internal_maintenance_only`.

Aggiornamento V1.26.0 planning: il prossimo salto del ramo non e aggiungere
piu blocchi al prompt, ma definire un router di context pack. Il contesto deve
restare una superficie cognitiva instradata: spine minima sempre attiva,
pack per source-sensitive/temporal/project/emotional work, e futuri pack
embodied per sensori e attuatori.

## Sviluppi precedenti

- Memory Context Pipeline v0.
- Runtime context stratificato.
- Temporal context con clock unico.
- Platform language configurata.
- Profilo, privacy e locale operativi.
- Recent runtime events nel turno successivo.
- V1.6.0: registro blocchi runtime/model/UI e inspector `Modello` per verificare
  ordine, contenuto e ridondanze dei dati inviati al modello.
- V1.7.0: lifecycle UI dei blocchi streaming con riconciliazione live/persisted
  a fine turno.
- V1.7.1: prompt fix per trattare i blocchi runtime/memory gia iniettati come
  evidenza sufficiente nei turni contestuali semplici.
- V1.9.0: `metacognitive.context` shadow e rendering UI dedicato per valutare
  trigger/lezioni candidate prima di attivare retrieval metacognitivo reale.
- V1.26.0 planning: baseline documentale per context pack, classificazione
  organi/fonti/capacita, degradazione sotto budget e shadow router futuro.

## Evolutive

- Implementare un registry di context pack in shadow mode prima di modificare
  l'input model-facing.
- Rendere `scarlet_state` aggiornabile da API dedicate.
- Separare dati sessione, dati messaggio, dati utente e dati ambiente con
  policy ancora piu esplicite.
- Aggiungere contesto ambiente reale quando esisteranno operativita esterne.
- Aggiungere receipt/evidence id per ogni blocco percepito.
- Valutare quali blocchi aiutano davvero il routing dello sforzo e quali
  rischiano di spingere M3 verso analisi eccessive.
- Per embodiment futuro, inviare al modello sintesi di scena/audio/azione e
  non stream sensoriali raw, con pack attuativi sempre gated da sicurezza.
