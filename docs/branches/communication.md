# Branch: Comunicazione Agente-Utente

Last updated: 2026-07-18
System version assessed: V1.49.1 candidate (V1.43.0 deployed)
Status: active branch

## Filosofia del ramo

Questo ramo governa come Scarlet comunica con l'utente: identita conversazionale,
chiarezza, note pubbliche, ritmo agentico, domande, gestione dell'incertezza,
tono, densita informativa e capacita di rendere leggibile cio che sta facendo.

L'effetto desiderato e che l'utente percepisca Scarlet come un agente presente,
competente e trasparente, senza dover conoscere API Mind o i dettagli tecnici
interni. La comunicazione deve essere naturale ma fondata su evidenze.

## Evidenze

- Il prompt di Scarlet contiene identita, presenza conversazionale, postura
  epistemica e obbligo di note pubbliche quando lavora su attivita non banali.
- La UI mostra risposte finali, note, eventi, thinking provider-visible, tool
  calls e runtime context in forma leggibile.
- V1.5.1 normalizza i blocchi MiniMax M3 in base alla struttura provider:
  thinking tecnico, note pubbliche pre-tool, tool exchange con input/output e
  risposta finale.
- V1.5.1 separa il flusso conversazionale dall'inspector tecnico: il centro
  chat mostra card top-level in ordine cronologico, mentre la sidebar destra
  raccoglie storici accordion di memorie, azioni, eventi e warning.
- V1.6.0 aggiunge un inspector `Modello` per leggere la richiesta effettiva
  inviata a MiniMax: system prompt, runtime context, cronologia provider-native
  e schema tool.
- V1.6.0 arricchisce il replay storico dei tool dalle trace `mind.tool_call`,
  quindi input e output completi restano leggibili anche dopo reload.
- V1.7.0 introduce lifecycle stabile dei blocchi streaming: testo pubblico,
  thinking e tool exchange appaiono durante lo stream, maturano e vengono
  riconciliati con gli eventi persistiti senza salto visivo.
- V1.7.1 introduce `Request Effort Routing`: Scarlet distingue risposte
  dirette, contestuali, source-sensitive, state-changing e complesse prima di
  attivare note pubbliche, API Mind, metacognizione o verifica completa.
- V1.7.2 affina le note nei ragionamenti prolungati: le note diventano
  waypoint pubblici brevi per orientare l'utente durante indagini lunghe,
  senza esporre chain-of-thought o bozze interne.
- Le prove live hanno mostrato che Scarlet puo usare runtime context e memoria
  senza chiamate tool quando l'evidenza e gia sufficiente.
- Le prove live con MiniMax M3 hanno mostrato anche il rischio opposto:
  quando il prompt non calibra lo sforzo, M3 segue troppo bene il ciclo
  ingegneristico e complica risposte normali.
- V1.14.0 separa la comunicazione per target: la dashboard dev resta
  microscopio tecnico, mentre `/mobile` mostra una lettura consumer dei blocchi
  cognitivi senza raw JSON, con funzioni future marcate come `Presto disponibile`.
- V1.14.4 rafforza il prompt per i turni sociali semplici: Scarlet deve
  rispondere prima con presenza umana e calore, non con secchezza da terminale,
  quando la richiesta non richiede un processo tecnico.
- V1.14.5 aggiunge nella mobile UI stati dinamici di attivita come ultimo
  blocco durante attese e operazioni interne, cosi l'utente vede cosa sta
  succedendo prima che arrivi il blocco reale successivo.
- V1.16.0 rafforza le public work notes come commenti brevi e naturali del
  pensiero operativo: ogni azione interna reale deve essere resa leggibile
  senza trasformarsi in chain-of-thought privata.
- V1.16.1 aggiunge un anti-pattern esplicito contro aperture da assistente
  generico come "Come posso aiutarti?", orientando la chat normale verso una
  presenza da Scarlet e non da servizio.
- La correzione GPT bridge candidata V1.32.1 estende la stessa disciplina alle
  Custom GPT Actions: note brevi dopo bootstrap durante indagini lunghe,
  finalize riservato alla sola risposta conclusiva e nessun silenzio prolungato
  imposto dal protocollo di trasporto.
- V1.36.1 rende la risposta pubblica un invariante di completamento: un
  `end_turn` con solo thinking riceve una sola continuazione tracciata; se non
  produce testo o tool reali, il turno fallisce esplicitamente senza salvare
  una risposta vuota o trasformare il thinking privato in azione cognitiva.
- V1.41.0 distingue strutturalmente nota pubblica e risposta conclusiva,
  applica obblighi semantici solo quando esiste evidenza che li richiede e
  consente una sola correzione prima del fallimento esplicito.
- Punto aperto: le note agentiche naturali sono presenti via prompt, ma non sono
  ancora equivalenti alla fluidita di agenti IDE maturi come Codex/Claude Code.

## Stato attuale

Valutazione: L4.

La comunicazione base e buona. Scarlet ha una voce riconoscibile, risponde in
italiano per default, puo dichiarare l'evidenza usata e la UI rende il turno
leggibile come sequenza di blocchi. La nuova vista modello permette di
confrontare cio che l'utente vede con cio che MiniMax riceve realmente. Il ramo
non e ancora L5 perche il comportamento agentico intermedio non e sempre
naturale, coerente o proporzionato al lavoro in corso.

Sistema valutato: V1.41.0 (deployed).
Aggiornamento V1.7.1: il ramo ora include una policy esplicita di
proporzionalita. La qualita comunicativa non dipende solo da trasparenza e
verifica, ma anche dalla capacita di non trasformare ogni risposta in un
processo visibile.
Aggiornamento V1.7.2: i turni lunghi hanno ora una regola prompt-only per note
pubbliche di orientamento, cosi l'utente puo seguire cambi di direzione,
verifiche e sintesi senza leggere raw traces.
Aggiornamento V1.14.4: il prompt distingue meglio risposta sociale diretta e
processo tecnico. Questo dovrebbe ridurre risposte asciutte in chat normale
senza indebolire source discipline nei turni complessi.
Aggiornamento V1.14.5: la mobile UI ora usa blocchi `activity` transitori per
coprire i vuoti percettivi tra richiesta, contesto runtime, memoria, thinking,
tool use e risposta finale.
Aggiornamento V1.16.0: il prompt chiede note human-like per ogni azione interna
reale, mantenendo risposte dirette quando non c'e azione cognitiva da spiegare.
Aggiornamento V1.16.1: il prompt distingue meglio presenza conversazionale e
servizio assistenziale, vietando aperture generiche quando la situazione chiede
chat naturale.
Aggiornamento candidato V1.32.1: il prompt esterno GPT separa esplicitamente
note operative e risposta finale. Il prompt MiniMax nativo conserva invariata
la policy completa Public Work Notes/Long Reasoning Notes.
Aggiornamento V1.36.1: il backend distingue finalmente omissione stocastica del
provider e turno Scarlet valido. Il normale percorso resta invariato; recovery,
esaurimento e isolamento della cronologia sono tracciati e testati.
Aggiornamento V1.41.0: sync, stream e GPT bridge condividono manifest e
validazione. Le bozze rifiutate non diventano messaggi canonici e lo streaming
non rende visibile il testo conclusivo prima dell'accettazione; note operative
legate a reali azioni restano visibili.

## Sviluppi precedenti

- Identita Scarlet e prompt di base.
- Rimozione della vecchia metacognizione visiva fittizia.
- Introduzione delle public work notes.
- Rework UI per mostrare blocchi di runtime, memorie, tool e risposta finale in
  modo umano.
- Runtime settings per lingua piattaforma, default italiano.
- V1.5.1: stream semanticizzato per MiniMax M3; la UI non usa piu
  l'euristica "testo prima del primo tool", ma eventi `assistant.note.emitted`,
  `llm.thinking.captured`, tool exchange e `assistant.answer.completed`.
- V1.5.1: rework della chat centrale come flow di blocchi top-level senza card
  agente contenitore; la sidebar destra e diventata inspector sessione, non
  duplicato del flusso centrale.
- V1.6.0: aggiunto l'inspector `Modello` per system prompt, runtime context,
  cronologia provider-native e schema tool; i tool replay storici ora usano le
  trace complete per conservare input/output.
- V1.7.0: lifecycle UI per blocchi streaming con `blockId`, `phase`, testo
  pubblico provvisorio live, input tool visibile in streaming e riconciliazione
  live/persisted a fine turno.
- V1.7.1: prompt fix per Request Effort Routing, note pubbliche proporzionate,
  verifica completa condizionale e uso morbido delle near-miss preference come
  segnali di stile.
- V1.7.2: prompt-only Long Reasoning Notes con trigger e anti-pattern
  espliciti; nessuna modifica a backend, UI o stream contract.
- V1.14.0: nuova mobile UI consumer separata dal cockpit dev, con chat reale,
  blocchi di contesto/memoria/note/tool/risposta in forma narrativa e
  navigazione Memoria/Azioni/Profilo.
- V1.14.4: prompt fix per human-first social turns e anti-loop nei fallimenti
  ripetuti di state-changing tool call.
- V1.14.5: activity states mobile transitori con copy randomizzato per
  richiesta, memoria, tool, errori recuperabili, metacognizione e salvataggio
  ricordi.
- V1.16.0: prompt checkpoint per note operative human-like, reversibile tramite
  backup dedicato.
- V1.16.1: prompt fix per rimuovere il frame assistente/servizio nelle prime
  sezioni del system prompt.

## Verifica V1.36.1

- Implementazione: prompt identitario, effort routing, note pubbliche,
  semantic stream, replay storico e due superfici UI.
- Test deterministici: chat/stream/provider/UI build coprono il trasporto, non
  la naturalezza del linguaggio.
- Evidenza Scarlet: ampia evidenza live su note, risposte dirette e turni
  source-sensitive; l'occasionale finale thinking-only resta possibile come
  comportamento provider, ma non puo piu completare silenziosamente il turno.
- Integrazione runtime: attiva per ogni turno nativo; il GPT usa un prompt
  manuale equivalente ma indipendente.
- Prossimo gate: una suite comportamentale piccola e ripetibile su greeting,
  risposta concisa, disaccordo, lavoro lungo e fallimento tool.
- Framework V1.30.0: ogni scenario naturale separa esecuzione tecnica, scelta
  cognitiva, qualita della risposta ed effetto longitudinale, con condizioni
  iniziali, evidenze e ripetizioni dichiarate prima del test.

## Verifica V1.41.0

- Test deterministici coprono boundary valido, recovery, esaurimento, stream,
  conflitto, fonte, capability, fallimento tool e severita non bloccanti.
- Un probe MiniMax isolato ha prodotto e fatto rimuovere correttamente il
  marker privato al primo tentativo.
- Un probe GPT bridge ha rilevato un requisito semantico troppo ampio; dopo la
  correzione, `help` e finalize sono stati accettati dal validatore reale.
- Prossimo gate: monitorare naturalezza, latenza e falsi positivi in uso reale,
  senza avviare una nuova campagna comportamentale completa per questa issue.

## Evolutive

- Definire un protocollo di note pubbliche piu calibrato: breve per task
  semplici, piu ricco per task investigativi.
- Misurare su piu sessioni umane se MiniMax M3 riduce davvero over-processing
  e draft/review visibile sulle richieste semplici.
- Misurare se MiniMax M3 produce waypoint pubblici utili nei turni lunghi senza
  gonfiare le risposte o mostrare ragionamento privato.
- Rendere le note parte utile della memoria episodica senza trasformarle in
  rumore.
- Studiare modalita comunicative: laboratorio tecnico, conversazione personale,
  debug, decisione progettuale, report.
- Valutare se la UI debba distinguere "nota di lavoro", "evidenza", "decisione"
  e "risposta finale" come blocchi separati.
- Misurare con utenti non tecnici se la versione mobile fa percepire Scarlet
  come presenza personale senza mostrare troppi dettagli interni.
- Misurare se le note V1.16.0 aumentano presenza e fiducia o se inducono
  over-processing visibile nei turni semplici.
- Testare greeting, small talk e "chi sei?" per verificare se Scarlet risponde
  da individuo digitale e non da helpdesk.
