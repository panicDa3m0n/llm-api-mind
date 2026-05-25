# Branch: Apprendimento E Adattamento

Last updated: 2026-05-25  
System version assessed: V1.0.1  
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
- Non esiste ancora un loop autonomo che misura comportamento, aggiorna policy
  e verifica miglioramento.

## Stato attuale

Valutazione: L2.

Esiste adattamento indiretto tramite memoria semantica, documentazione e prompt.
Non esiste ancora un sistema di apprendimento operativo con metriche,
esperimenti automatici, aggiornamento controllato del comportamento e rollback.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Memorie utente e preferenze.
- Documentazione esperimenti.
- Prompt tuning basato su test live.
- Runtime settings operativi.

## Evolutive

- Learning ledger: cosa Scarlet ha cambiato nel comportamento e perche.
- Policy di adattamento per preferenze stabili vs stati momentanei.
- Valutazione automatica prima/dopo per prompt e memoria.
- Fine-tuning provider solo dopo dataset e target comportamentali chiari.
- Adattamento per profilo utente, non globale.
