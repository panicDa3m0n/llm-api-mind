# Branch: Operativita Su Mondo Esterno

Last updated: 2026-07-27
System version assessed: V1.60.0 development target
Status: planned branch with isolated device prototype

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
- V1.58.0 aggiunge soltanto probe espliciti per notifica locale e feedback
  aptico, con receipt nel ledger Device Exploration. Non sono tool concessi a
  Scarlet e non costituiscono autonomia esterna.
- V1.58.1 verifica sul device consegna e apertura della notifica, feedback
  aptico e transizioni rete reali; nessuna di queste ricevute abilita ancora
  operativita autonoma.
- V1.60.0 introduce autonomia cognitiva interna e un inbox percettivo
  navigabile. Non concede a Scarlet notifiche utente, azioni sul device o tool
  esterni: un ciclo autonomo puo ispezionare e modificare soltanto organi gia
  supportati.

## Stato attuale

Valutazione: L1 per Scarlet; L2 per il laboratorio device isolato.

Il ramo e quasi interamente futuro. L'infrastruttura di eventi, trace, UI e
schema potra supportarlo, ma oggi Scarlet non ha operativita esterna ampia
integrata nella propria API Mind.

Sistema valutato: V1.29.1.

Aggiornamento V1.58.0: il Product UI puo richiedere manualmente una notifica
locale o un feedback aptico e registrarne esito/errore. Il confine resta
tecnico e umano-iniziato: nessun comando model-facing, policy di azione,
scheduler agentico o collegamento ai context pack e stato introdotto.

Aggiornamento V1.60.0: esiste uno scheduler agentico per cognizione interna,
ma non un dispatcher di operativita esterna. L'eventuale iniziativa verso
l'umano e ogni azione reale richiedono record, permessi e ricevute separati.

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
