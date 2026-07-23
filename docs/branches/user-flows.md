# Branch: Gestione Flussi Utente

Last updated: 2026-07-24
System version assessed: V1.55.2 development target
Status: first Product UI Core integration active

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
- V1.55.0 collega `/prototype` a health, sessioni, messaggi, Stream V2,
  memorie, profilo e impostazioni reali. Ogni controllo senza contratto
  consumer apre il modale centrale `Funzione non disponibile` e non simula
  successi.
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
- Il target V1.54.0 estende l'ingresso di `/prototype` con loader, controllo
  aggiornamento simulato, transizione automatica, Login/Registrazione e
  credenziali fake verificabili senza collegare un backend account.
- Il saluto video viene precaricato in parallelo ai controlli della splash,
  resta fermo e nascosto fino al `100%`, viene riprodotto una sola volta e
  abilita il passaggio al Login soltanto al termine.
- Il primo accesso fake conduce ora a una Home responsive con Scarlet, riepiloghi,
  ultimi ricordi e sessioni recenti; dati e azioni restano fixture locali fino
  all'approvazione dell'intero percorso di schermate.
- La shell post-login collega ora Home, Chat, Memoria, Sessioni e Profilo con
  prime versioni coerenti e funzioni locali simulate. Lo scroll finestra usa un
  contratto documento scoped al prototipo e non eredita piu il blocco del
  cockpit.
- Splash termina ora sulla readiness reale di ritratto, font e media, poi
  riproduce il primo `52%` del saluto precaricato a velocita naturale `1x` e
  apre subito Login.
- L'accesso fake conserva in local storage username e ultima schermata; reload
  e riapertura riprendono il flusso, mentre logout cancella esplicitamente la
  sessione.
- Chat usa un layout app a viewport intera: header Scarlet compatto, soli
  messaggi scorrevoli, composer sempre visibile e dock mobile riservato.
- L'header Product ripetitivo e stato rimosso: un dock inferiore a cinque voci
  gestisce la navigazione sia mobile sia desktop, mentre logout vive in alto
  nelle Impostazioni.
- Chat, Memoria, Sessioni e Profilo espongono i JSON reali disponibili;
  Impostazioni persiste i campi supportati e apre il modale di indisponibilita
  per regole prompt, privacy, manutenzione ed extra senza contratto consumer.
- Ogni turno Chat usa eventi V2 reali e distingue testo autoriale, proiezione
  consumer, terminali falliti e confine debug/private.

## Stato attuale

Valutazione: L3 per il Product UI connesso; i client precedenti restano L2/L3.

Esistono ora tre superfici distinte: cockpit tecnico, precedente client mobile
consumer e Product UI `/prototype`. Il Product UI aggiunge
splash/autenticazione locale/Home e collega health, riepiloghi, ricordi,
sessioni, Chat V2, profilo e impostazioni ai contratti Core esistenti.
L'autenticazione locale persiste la schermata ma non e un contratto di
sicurezza. Le azioni senza contratto aprono il modale centrale e non simulano
successi. Non esistono ancora account backend, multiutente, session close
esplicito, revisione guidata memoria o workflow privacy avanzati. V1.55.1
aggiunge un gate browser ripetibile e preserva un `turn.failed` come singola
bolla consumer dopo reload.
V1.55.2 rende visibili i movimenti reali del turno, aggiunge ricevute evento
centrate e una preferenza locale per evidenze protette metadata-only. Le
schermate lunghe mantengono scroll documento naturale; solo Chat usa il layout
interno a viewport.

Sistema valutato: V1.55.2 development target.

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
- Target V1.54.0: entry controller, loader/update check simulato, saluto
  precaricato come transizione conclusiva, Login/Registrazione responsive,
  credenziali fake e shell responsive Home/Chat/Memoria/Sessioni/Profilo con
  dati e funzioni dimostrativi; readiness reale, sessione locale persistente,
  Chat a viewport e pannelli JSON completano il secondo passaggio.

## Verifica V1.55.1

- Il gate Playwright/Edge attraversa Splash/video, Login, registrazione
  indisponibile, persistenza, Home, sessioni, Memoria, Impostazioni, modali e
  logout.
- Un turno MiniMax reale ha completato Stream V2 dalla UI.
- Un turno fallito persistito viene ricostruito dopo replay come una sola
  bolla italiana, senza duplicazione di trasporto.
- Desktop `1440x1000` e mobile `390x844` passano senza errori console/rete,
  overflow orizzontale o regressioni dello scroll/layout Chat.

## Verifica V1.55.2

- Un turno MiniMax M3 reale mostra stato pending, memoria, contesto, richiesta
  e thinking prima della risposta.
- Replay completo e fallito ricostruiscono bolle e terminali senza duplicati.
- I modali evento sono centrati e navigabili su desktop/mobile; contesto e
  memoria espongono fatti coerenti e i tool raggruppano il lifecycle.
- `Evidenze private` persiste al reload, si cancella al logout e non espone il
  testo di `llm.thinking.captured`.
- Il gate CSS vieta height/min-height sui root Product e prova lo scroll reale
  di Home separatamente dal layout Chat a viewport.

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
- Sostituzione della sessione local-storage con autenticazione, scadenza,
  revoca e storage nativo sicuri.
- Compilazione delle preferenze approvate in regole system-prompt tracciabili.
- Packaging Capacitor/Android dopo stabilizzazione visiva della mobile app.
- Autenticazione reale, persistenza account e sicurezza solo dopo approvazione
  del flusso visuale e definizione del relativo contratto backend.
- Brand pass consumer: icona, visual identity Scarlet, motion e schermata
  iniziale senza trasformare la UI in una landing page.
