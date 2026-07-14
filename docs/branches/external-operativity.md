# Branch: Operativita Su Mondo Esterno

Last updated: 2026-07-13
System version assessed: V1.29.1
Status: planned branch

## Filosofia del ramo

Questo ramo riguarda la capacita di Scarlet di agire davvero fuori dalla pura
cognizione interna: file, codice, ambienti, browser, calendari, email,
servizi, automazioni, API esterne e sistemi reali.

L'effetto desiderato e passare da agente che ragiona a agente che opera, con
permessi, tracciabilita, rollback e conferme dove necessario.

## Evidenze

- API Mind oggi e soprattutto cognitiva: memoria, sessioni, schema,
  metacognizione.
- Il progetto ha discusso la CLI ma l'ha rimandata per non complicare la
  superficie.
- V1.25.4 stabilizza `mind_shell` come unica superficie model-facing mentre
  gli endpoint restano interni/debug/manutenzione.
- V1.26.0 planning separa l'operativita futura in context pack gated: agire su
  mondo esterno o corpo robotico richiedera perception, safety, conferme,
  attuatori e ricevute nello stesso pacchetto operativo.
- Non esiste ancora una suite di tool esterni concessi a Scarlet runtime.

## Stato attuale

Valutazione: L1.

Il ramo e quasi interamente futuro. L'infrastruttura di eventi, trace, UI e
schema potra supportarlo, ma oggi Scarlet non ha operativita esterna ampia
integrata nella propria API Mind.

Sistema valutato: V1.29.1.

## Sviluppi precedenti

- Discussione API vs CLI per API Mind.
- Decisione attuale: `mind_shell` e la superficie model-facing; endpoint
  classici restano supporto interno/debug/manutenzione.
- Runtime events come possibile base per azioni osservabili.
- V1.26.0 planning: `docs/runtime-context-packs.md` definisce che azioni
  embodied/attuative future devono essere context pack gated, non semplice
  contesto aggiunto al prompt.

## Verifica V1.29.1

- Implementazione: nessun tool operativo esterno concesso a Scarlet; eventi,
  trace e shell sono solo substrato.
- Test deterministici e live: assenti per azioni su file, browser, servizi o
  corpo.
- Integrazione runtime: assente.
- Prossimo gate: capability registry con rischio, permesso, reversibilita,
  conferma, timeout e receipt; per embodiment percezione e safety devono essere
  tightly coupled all'attuazione.

## Evolutive

- Permission model per azioni esterne.
- Tool registry con capability, rischio, rollback e audit.
- Ambiente file/codice controllato.
- Browser/web task con ricevute.
- Integrazioni calendario/email solo dopo privacy e conferme chiare.
- Per body robotico futuro: nessuna attuazione fisica senza pack dedicato che
  includa percezione corrente, vincoli safety, piano, conferma o politica di
  autorizzazione, ed esito tracciato.
