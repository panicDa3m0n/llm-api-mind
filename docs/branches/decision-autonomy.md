# Branch: Autonomia Decisionale

Last updated: 2026-06-26
System version assessed: V1.21.0
Status: first volition register standalone surface closed

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

## Stato attuale

Valutazione: L2/L3.

Scarlet ha autonomia guidata da prompt e tool disponibili. Il registro
volitivo aggiunge una prima forma di direzione interna tracciabile:
`POST /mind/volition` gestisce intenzioni latenti e V1.21.0 aggiunge
`list_due` per future code di cicli autonomi. Non esiste ancora esecuzione
autonoma dei cicli.

Sistema valutato: V1.21.0.

## Sviluppi precedenti

- Tool loop model-controlled unbounded.
- API Mind come cognizione interna.
- Prompt per salvataggio memoria autonomo.
- Endpoint-local error guides.
- V1.19.0 `intention_records`, `intention_links`, `/mind/volition`.
- V1.21.0 `volition.list_due` per review queue senza chat injection.

## Evolutive

- Decision policy machine-readable.
- Validator per promesse non mantenute, claim forti, conflitti ignorati.
- Autonomy budget non come limite numerico, ma come criterio di costo/beneficio.
- Receipt per decisioni autonome importanti.
- Modalita "chiedi prima" per azioni esterne o irreversibili.
- Cicli autonomi che consumano intenzioni dovute senza disturbare la chat
  utente.
