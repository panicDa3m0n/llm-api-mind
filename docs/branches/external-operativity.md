# Branch: Operativita Su Mondo Esterno

Last updated: 2026-05-25  
System version assessed: V1.0.1  
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
- Non esiste ancora una suite di tool esterni concessi a Scarlet runtime.

## Stato attuale

Valutazione: L1.

Il ramo e quasi interamente futuro. L'infrastruttura di eventi, trace, UI e
schema potra supportarlo, ma oggi Scarlet non ha operativita esterna ampia
integrata nella propria API Mind.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Discussione API vs CLI per API Mind.
- Decisione temporanea: mantenere API come superficie primaria.
- Runtime events come possibile base per azioni osservabili.

## Evolutive

- Permission model per azioni esterne.
- Tool registry con capability, rischio, rollback e audit.
- Ambiente file/codice controllato.
- Browser/web task con ricevute.
- Integrazioni calendario/email solo dopo privacy e conferme chiare.
