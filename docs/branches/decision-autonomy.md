# Branch: Autonomia Decisionale

Last updated: 2026-05-25  
System version assessed: V1.0.1  
Status: early branch

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

## Stato attuale

Valutazione: L2.

Scarlet ha autonomia guidata da prompt e tool disponibili. Non esistono ancora
policy backend/validatori che rendano certe decisioni obbligatorie o sicure.
L'autonomia e quindi utile, ma fragile in casi limite.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Tool loop model-controlled unbounded.
- API Mind come cognizione interna.
- Prompt per salvataggio memoria autonomo.
- Endpoint-local error guides.

## Evolutive

- Decision policy machine-readable.
- Validator per promesse non mantenute, claim forti, conflitti ignorati.
- Autonomy budget non come limite numerico, ma come criterio di costo/beneficio.
- Receipt per decisioni autonome importanti.
- Modalita "chiedi prima" per azioni esterne o irreversibili.
