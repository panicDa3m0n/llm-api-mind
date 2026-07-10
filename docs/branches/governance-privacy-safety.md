# Branch: Governance, Privacy E Sicurezza Cognitiva

Last updated: 2026-07-10
System version assessed: V1.27.0
Status: early branch

## Filosofia del ramo

Questo ramo governa privacy, separazione profili, consenso, sicurezza
cognitiva, audit, dati sensibili, cancellazione, deprecazione e limiti
operativi.

L'effetto desiderato e che Scarlet possa crescere in memoria e operativita
senza mescolare utenti, abusare dati, o agire fuori da confini espliciti.

## Evidenze

- Esiste un profilo attivo locale con `profile_id`.
- Esiste `privacy_scope` nel runtime context.
- Le memorie sono ancora in un database locale versionato per laboratorio, non
  in un modello privacy production.
- La governance degli endpoint distingue campi backend-owned e Scarlet-owned.
- V1.27.0 distingue esplicitamente DB `production`, `laboratory`, `test` e
  `preliminary`; il runtime rifiuta ambienti ambigui e il deploy VPS deve
  mantenere il mount dati fuori dal trasferimento di codice.
- V1.26.0 planning richiede che i futuri context pack rispettino profilo,
  privacy scope, autorita della fonte e confini di sicurezza prima di
  includere dati in prompt o azioni embodied.

## Stato attuale

Valutazione: L2.

Il ramo ha i primi ganci strutturali, ma non e maturo. Non esiste vero
multiutente, non esiste cancellazione privacy completa, non esistono policy
di consenso avanzate o access control su memorie.

Sistema valutato: V1.27.0.

## Sviluppi precedenti

- Lab DB versioning policy.
- Field ownership policy.
- Runtime profile id e privacy scope.
- Prompt: non fondere futuri profili utente senza collegamento backend.
- Context-pack planning: ogni pack deve dichiarare owner, privacy boundary,
  safety gate e degradazione.
- Topologia DB e preflight read-only: i dati reali VPS sono un confine
  operativo distinto dalla snapshot laboratorio e dai DB disposable.

## Evolutive

- Separazione memoria per profilo.
- Privacy dashboard per esportare/cancellare/correggere dati.
- Memory access control per scope e sensibilita.
- Audit trail user-facing per azioni cognitive importanti.
- Policy per dati sanitari, personali e relazionali.
- Gating esplicito per futuri pack di actuation fisica, tool esterni o dati
  sensoriali sensibili.
