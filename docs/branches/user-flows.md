# Branch: Gestione Flussi Utente

Last updated: 2026-07-19
System version assessed: V1.52.0 candidate
Status: static Product UI approval gate active

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
- V1.14.0 aggiunge una superficie mobile consumer separata su `/mobile`, mentre
  `/` resta il cockpit dev. La mobile UI usa dati reali gia disponibili
  (chat streaming, sessioni, memoria, profilo, settings) e marca le funzioni
  future come `Presto disponibile`.
- V1.14.2 pubblica una preview mobile esterna protetta da Basic Auth sotto
  `https://honeylabs.cloud/scarlet/`, con API demo separate sotto
  `/scarlet-api/`.
- V1.14.3 integra feedback da uso reale su telefono: contesto tecnico e
  sessioni recenti sono in un drawer laterale, la chat ha piu spazio verticale,
  e Memoria/Azioni/Profilo scorrono come pagine intere.
- V1.14.5 riduce la latenza percepita della chat mobile con stati dinamici
  transitori in coda al flusso, sostituiti dai blocchi reali appena arrivano
  stream, tool result o risposta finale.
- V1.52.0 aggiunge la superficie isolata `/prototype`: un solo albero Product
  UI responsive per mobile e desktop, cognizione pubblica compatta, sessioni,
  memorie, stato, impostazioni, recovery e lente sviluppatore alimentati
  esclusivamente da fixture V2 realistiche.

## Stato attuale

Valutazione: L3 per il prototipo statico; i client reali restano L2/L3.

Esistono ora due superfici distinte: cockpit tecnico per sviluppo e app mobile
consumer per uso normale. La mobile app abilita chat, memoria visibile, profilo
e settings reali, ma non ha ancora onboarding, multiutente, session close
esplicito, revisione guidata memoria o workflow privacy avanzati.

Il prototipo V1.52.0 e verificato in browser ma deliberatamente scollegato dai
dati runtime. L'approvazione del proprietario e obbligatoria prima che SCA-50
estragga le primitive responsive o SCA-49 lo connetta al Core.

Sistema valutato: V1.52.0 candidate.

## Sviluppi precedenti

- Sidebar con sessioni recenti.
- Dashboard Tailwind con tab Memorie, Profilo, Impostazioni e Agent Stream.
- Runtime settings persistenti.
- Profilo operativo locale e privacy scope.
- V1.14.0: route `/mobile` con navigazione Chat/Memoria/Azioni/Profilo,
  layout mobile-only, scroll interni e funzioni future contrassegnate come
  `Presto disponibile`.
- V1.14.2: supporto deploy path-based con API prefix configurabile e preview
  protetta su VPS HoneyLabs senza interferire con i container HoneyLabs
  esistenti.
- V1.14.3: drawer mobile per contesto/sessioni e correzione dello scroll
  page-level nelle sezioni Memoria, Azioni e Profilo.
- V1.14.5: blocco mobile `activity` per richiesta in corso, contesto,
  retrieval memoria, salvataggio ricordi, tool waits, errori recuperabili e
  metacognizione.
- V1.52.0: route Product UI statica, pipeline Tailwind CSS 4, anteprima a sei
  stati e screenshot desktop/mobile versionati.

## Verifica V1.52.0

- Implementazione: cockpit tecnico completo e mobile consumer funzionante su
  chat/sessioni/memoria/profilo/settings.
- Test deterministici: contratti API e build TypeScript; non esiste una suite
  browser E2E stabile.
- Evidenza utente: preview mobile usata e corretta su telefono; workflow
  avanzati assenti.
- Integrazione runtime: attiva, ma i file `App.tsx` e `MobileApp.tsx` sono
  monoliti rispettivamente di circa 4.5k e 1.8k righe.
- Browser reale: 1440x1000 e 390x844, screenshot, interazioni, assenza di
  overflow orizzontale e console pulita.
- Build: produzione TypeScript/Vite e audit npm senza vulnerabilita.
- Confine: nessuna chiamata API e nessuna modifica ai consumer stream reali.
- Prossimo gate: approvazione esplicita, poi componentizzazione SCA-50 e
  integrazione Core SCA-49.

## Evolutive

- Onboarding iniziale per nome, lingua, paese, privacy e stile comunicativo.
- Flusso di revisione memoria personale: cosa Scarlet sa dell'utente, cosa e
  attivo, cosa e deprecato.
- Session lifecycle: attiva, inattiva, chiusa, archiviata.
- Modalita privacy: locale singolo, profilo privato, multiutente futuro.
- Flussi per esportazione, cancellazione e correzione dati utente.
- Packaging Capacitor/Android dopo stabilizzazione visiva della mobile app.
- Brand pass consumer: icona, visual identity Scarlet, motion e schermata
  iniziale senza trasformare la UI in una landing page.
