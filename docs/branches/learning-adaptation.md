# Branch: Apprendimento E Adattamento

Last updated: 2026-07-09
System version assessed: V1.25.4
Status: early branch

## Filosofia del ramo

Questo ramo riguarda la capacita di Scarlet di migliorare il comportamento nel
tempo: adattarsi a preferenze, errori, correzioni, pattern utente, risultati
di test, decisioni progettuali e feedback.

Non coincide con fine-tuning. Nel progetto attuale l'apprendimento e prima di
tutto runtime learning: memoria, prompt, stato, evidenze, decisioni e policy.

## Evidenze

- Scarlet puo salvare preferenze e usarle in sessioni successive.
- Le decisioni progettuali vengono registrate in docs e memorie.
- Le correzioni dell'utente influenzano prompt e roadmap.
- Il probe live corretto del 2026-07-09 mostra adattamento reale tramite
  memoria preferenza cross-session, ma anche un limite: l'applicazione
  immediata dello stile richiesto non e garantita (`BUG-0061`).
- V1.26.0 planning indica che preferenze, lezioni e pattern utente dovranno
  entrare nei pack giusti invece di essere sempre presenti in ogni contesto.
- Non esiste ancora un loop autonomo che misura comportamento, aggiorna policy
  e verifica miglioramento.

## Stato attuale

Valutazione: L2.

Esiste adattamento indiretto tramite memoria semantica, documentazione e prompt.
Non esiste ancora un sistema di apprendimento operativo con metriche,
esperimenti automatici, aggiornamento controllato del comportamento e rollback.

Sistema valutato: V1.25.4.

## Sviluppi precedenti

- Memorie utente e preferenze.
- Documentazione esperimenti.
- Prompt tuning basato su test live.
- Runtime settings operativi.
- Context-pack planning per recuperare adattamenti solo quando utili al modo
  operativo corrente.

## Evolutive

- Learning ledger: cosa Scarlet ha cambiato nel comportamento e perche.
- Policy di adattamento per preferenze stabili vs stati momentanei.
- Valutazione automatica prima/dopo per prompt e memoria.
- Fine-tuning provider solo dopo dataset e target comportamentali chiari.
- Adattamento per profilo utente, non globale.
- Response-shape validator o pack policy per verificare che preferenze appena
  recuperate cambino davvero la forma della risposta quando sono rilevanti.
