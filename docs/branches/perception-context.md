# Branch: Percezione E Contesto

Last updated: 2026-05-25  
System version assessed: V1.0.1  
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

## Stato attuale

Valutazione: L4.

Il ramo e uno dei piu solidi. Il modello riceve blocchi chiari, tracciati e
renderizzati in UI. La percezione non e ancora completa perche mancano ambiente
esterno reale, device/app state avanzato, profilo multiutente e stato Scarlet
modificabile tramite API.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Memory Context Pipeline v0.
- Runtime context stratificato.
- Temporal context con clock unico.
- Platform language configurata.
- Profilo, privacy e locale operativi.
- Recent runtime events nel turno successivo.

## Evolutive

- Rendere `scarlet_state` aggiornabile da API dedicate.
- Separare dati sessione, dati messaggio, dati utente e dati ambiente con
  policy ancora piu esplicite.
- Aggiungere contesto ambiente reale quando esisteranno operativita esterne.
- Aggiungere receipt/evidence id per ogni blocco percepito.
