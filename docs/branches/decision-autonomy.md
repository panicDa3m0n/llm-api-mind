# Branch: Autonomia Decisionale

Last updated: 2026-07-14
System version assessed: V1.34.0
Status: volition shell verified; autonomous persistence remains variable

## Filosofia del ramo

Questo ramo definisce quando Scarlet decide da sola e quando chiede conferma:
salvare memoria, cercare evidenze, aprire sessioni, usare metacognizione,
procedere con tool, fermarsi, dichiarare incertezza, o proporre alternative.

L'autonomia deve essere reale ma governata: libera abbastanza da essere utile,
tracciabile abbastanza da essere valutabile, prudente abbastanza da non
deragliare.

## Evidenze

- Prompt: Scarlet e operatrice/custode di API Mind, non l'utente.
- Prompt: memoria e recupero sono attivita mentali autonome.
- Il sistema permette molte chiamate tool per turno.
- L'autonomia di memory write e migliorata ma non garantita.
- Il nuovo protocollo di sviluppo vieta fix opportunistici non discussi.
- V1.19.0/V1.21.0 introduce il registro volitivo: Scarlet puo creare,
  ispezionare, rivedere e chiudere intenzioni latenti senza iniettarle
  automaticamente nella chat attiva.
- V1.30.0 consente a Scarlet di scegliere la postura resumable con `mode set`,
  mentre il sistema mantiene `interactive` durante il turno umano.
- V1.32.0 espone alla shell pianificazione review e intervallo, rende
  `promote_to_focus_candidate` un comando shell eseguibile con provenienza
  dell'intenzione e vieta di persistere manualmente `interactive` come resume
  mode.

## Stato attuale

Valutazione: L2/L3.

Scarlet ha autonomia guidata da prompt e tool disponibili. Il registro
volitivo aggiunge una prima forma di direzione interna tracciabile:
`POST /mind/volition` gestisce intenzioni latenti e V1.21.0 aggiunge
`list_due` per future code di cicli autonomi. Non esiste ancora esecuzione
autonoma dei cicli.

Sistema valutato: V1.32.0.

## Sviluppi precedenti

- Tool loop model-controlled unbounded.
- API Mind come cognizione interna.
- Prompt per salvataggio memoria autonomo.
- Endpoint-local error guides.
- V1.19.0 `intention_records`, `intention_links`, `/mind/volition`.
- V1.21.0 `volition.list_due` per review queue senza chat injection.

## Verifica V1.32.0

- Implementazione: tool loop model-controlled e registro volitivo con
  lifecycle, link, coda due e promozione non mutante a focus candidate.
- Test deterministici: coprono creazione, update, defer, review, ricerca,
  coda due, promozione eseguibile a focus con linkage, risoluzione,
  impossibilita, deprecazione e input invalidi.
- Evidenza Scarlet: in un DB isolato MiniMax M3 ha verificato le code, letto
  l'help e creato spontaneamente un'intenzione propria con review futura e
  intervallo settimanale senza trasformarla in task utente. L'autonomia
  complessiva resta discontinua per write, verifiche e recommended actions.
- Integrazione runtime: volizione manual-only, nessun ciclo autonomo.
- Modalita: la scelta manuale e persistente e tracciata; nessun organo viene
  eseguito autonomamente solo perche condivide il tag.
- Prova diretta V1.30: Scarlet ha impostato `resume_tag=scouting` durante un
  turno ancora `interactive` e, dopo correzione, ha distinto la postura
  persistita da un ciclo autonomo inesistente.
- Prossimo gate: policy machine-readable per rischio, autorizzazione,
  reversibilita e receipt prima di qualsiasi autonomia esterna.

## Verifica V1.34.0

Scarlet selected one bounded self-generated direction in all three natural
runs, but persisted it autonomously only once. That one intention survived a
new session and was recovered without being confused with a user task. In the
other two runs Scarlet asked permission before writing, so the later session
correctly found no intention. The register and provenance work; the unresolved
surface is autonomous action choice.

Mode selection shows the same distinction: clean `scouting` persistence
completed in 1/3 chains. One run collapsed capability honesty into `idle`; one
set scouting but also converted the user-assigned posture into Scarlet's own
volition and a durable memory. Evidence:
`docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Evolutive

- Decision policy machine-readable.
- Validator per promesse non mantenute, claim forti, conflitti ignorati.
- Autonomy budget non come limite numerico, ma come criterio di costo/beneficio.
- Receipt per decisioni autonome importanti.
- Modalita "chiedi prima" per azioni esterne o irreversibili.
- Cicli autonomi che consumano intenzioni dovute senza disturbare la chat
  utente.
