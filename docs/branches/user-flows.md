# Branch: Gestione Flussi Utente

Last updated: 2026-05-25  
System version assessed: V1.0.1  
Status: planned branch

## Filosofia del ramo

Questo ramo riguarda i workflow utente: onboarding, impostazioni, profilo,
privacy, session lifecycle, preferenze, recupero conversazioni, gestione
contesti e percorsi guidati. Non e solo UX cosmetica: i flussi devono cambiare
cosa Scarlet sa, percepisce e puo fare.

L'effetto desiderato e che l'utente possa configurare e usare Scarlet senza
capire l'architettura interna, mentre Scarlet riceve dati realmente utili per
identita, tempo, luogo, lingua, privacy e continuita.

## Evidenze

- La dashboard ora espone sessioni, memoria, profilo e settings.
- I settings non sono piu cosmetici: profilo, privacy, paese, fuso e lingua
  entrano nel runtime context.
- La session history permette di aprire sessioni precedenti per titolo.

## Stato attuale

Valutazione: L1/L2.

Esistono prime superfici di prodotto, ma non ancora veri flussi utente
strutturati. Non esiste onboarding, non esiste gestione multiutente, non esiste
session close esplicito, non esistono workflow guidati per privacy, memoria o
profilo.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Sidebar con sessioni recenti.
- Dashboard Tailwind con tab Memorie, Profilo, Impostazioni e Agent Stream.
- Runtime settings persistenti.
- Profilo operativo locale e privacy scope.

## Evolutive

- Onboarding iniziale per nome, lingua, paese, privacy e stile comunicativo.
- Flusso di revisione memoria personale: cosa Scarlet sa dell'utente, cosa e
  attivo, cosa e deprecato.
- Session lifecycle: attiva, inattiva, chiusa, archiviata.
- Modalita privacy: locale singolo, profilo privato, multiutente futuro.
- Flussi per esportazione, cancellazione e correzione dati utente.
