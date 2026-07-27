# Branch: Percezione E Contesto

Last updated: 2026-07-27
System version assessed: V1.61.0 development target
Status: active branch

## Filosofia del ramo

Questo ramo definisce cosa Scarlet percepisce prima di rispondere: tempo,
lingua, profilo, luogo operativo, sessione, messaggio corrente, memoria
automatica e organi dinamici esplicitamente abilitati. Eventi, capability e
stato tecnico restano superfici trace/on-demand quando non migliorano il turno.

L'effetto desiderato e trasformare il contesto backend in percezione operativa:
Scarlet non deve indovinare il mondo, deve ricevere blocchi affidabili e
stratificati.

## Evidenze

- Ogni turno costruisce `memory.context` e `runtime.context` prima della
  richiesta LLM.
- `runtime.context` conserva l'evidenza ricca; `model.context` conserva il
  documento esatto `scarlet-model-context-v2` inviato al modello.
- V2 espone sessione/utente/world compatti, due sessioni precedenti e tre
  blocchi memoria deduplicati con hook navigabili.
- Il runtime espone una sola fonte temporale valida: `session.now`, gia resa
  nel fuso dell'utente.
- `session.location` espone il locale configurato come paese, non GPS.
- `docs/block-registry.md` mappa ora i blocchi model-facing, i mirror
  compatibili, gli eventi trace-only e il rendering UI, cosi le future
  ottimizzazioni del context possono partire da evidenza reale.
- La UI espone un inspector `Modello` che mostra il `runtime_context` effettivo
  inviato a MiniMax e segnala i mirror top-level ridondanti rispetto ai blocchi
  canonici.
- V1.7.0 assegna identita e lifecycle ai blocchi stream UI, cosi la percezione
  visibile durante il turno resta collegata agli eventi persistiti.
- V1.7.1 chiarisce nel prompt che i blocchi gia presenti nel turno possono
  bastare per risposte contestuali: Scarlet non deve richiamare API Mind solo
  per confermare dati gia forniti dal runtime context o dalla memoria
  selezionata.
- V1.9.0 aggiunge una superficie shadow separata,
  `metacognitive.context`, visibile in trace/UI ma non model-facing in modalita
  default. In modalita controllata `inject` puo diventare un blocco
  `metacognitive_context` dentro `runtime_context.blocks`.
- V1.23.0 riduce rumore nel blocco automatico memoria: i conflitti
  model-facing derivano solo da facts atomici divergenti, non da semplice
  overlap di tag/token tra memorie selezionate.
- V1.25.4 allinea `message_context.api_mind.capabilities` e il mirror
  top-level `capabilities` al contratto model-facing `mind_shell`, separando
  le rotte endpoint interne/debug/manutenzione dalle vere capacita cognitive
  presentate a Scarlet.
- V1.26.0 planning introduce `docs/runtime-context-packs.md` come baseline per
  classificare organi, fonti e capacita in spine sempre attiva, pack
  condizionali, operazioni on-demand e manutenzione background-only.
- V1.30.0 misura separatamente le parti dell'input, registra l'uso reale del
  primo step provider e produce un piano di compattazione soltanto shadow.
- V1.30.0 introduce modalita agentiche a tag singolo e registry multi-tag per
  blocchi/organi, con `interactive` imposto durante i turni umani.
- V1.35.0 completa la review campo per campo del contesto preservato: solo
  focus, affect e lezioni metacognitive possono entrare condizionalmente nel
  modello attraverso allowlist esplicite.
- Ogni trace `model.context` registra ora un audit di inclusione/esclusione;
  Scarlet state legacy, dialogo duplicato, eventi generici e catalogo
  capability restano fuori dal documento V2.
- V1.58.0 introduce un Device Exploration Layer isolato che registra segnali
  Android raw e normalizzati per studio. Questi record non sono percezione di
  Scarlet e non entrano in runtime context, provider history, memoria o shell.
- V1.58.1 completa la verifica foreground di posizione, lifecycle, movimento,
  notifiche e rete, eliminando callback rete identici senza comprimere vere
  transizioni di trasporto.
- V1.59.0 introduce il registry semantico delle famiglie di contesto in shadow:
  distingue soggetto del dato, osservatore, tipo di evidenza, tag modalita,
  contratto di attivazione e policy obbligatorie senza modificare il V2
  model-facing.
- Le simulazioni MiniMax separano posizione del telefono e posizione umana,
  camera del device e futura visione di Scarlet, dispatch e receipt di una
  azione. Le policy funzionano quando composte come istruzioni, non quando
  nascoste dentro il JSON dei dati.
- V1.60.0 aggiunge un inbox percettivo append-only separato dal ledger Device
  Exploration: Scarlet vede soltanto un indice compatto dei canali disponibili
  e apre batch o eventi precisi con `perception status|open|read`.
- Il cursore di ispezione segue l'ordine di ricezione append-only, non il tempo
  osservato dal device, cosi eventi tardivi e batch oltre il limite non vengono
  saltati. Il tempo osservato resta evidenza distinta.
- Nessun adapter Android alimenta ancora l'inbox automaticamente; la presenza
  del contratto non promuove i dati sperimentali a percezione.

## Stato attuale

Valutazione: L4.

Il ramo e uno dei piu solidi. V1.29.0 separa esplicitamente evidenza interna e
proiezione model-facing, verifica provenienza e deduplica, e rende il documento
esatto ispezionabile in UI. La
percezione non e ancora completa perche mancano ambiente esterno reale,
device/app state avanzato, profilo multiutente e stato Scarlet modificabile
tramite API.

Sistema valutato: V1.36.0.
Aggiornamento V1.7.1: la percezione viene ora usata anche per calibrare lo
sforzo. Se il runtime context, la memoria selezionata o la history visibile
contengono gia l'evidenza sufficiente, il prompt istruisce Scarlet a non
duplicare la verifica con chiamate rituali.

Aggiornamento V1.9.0: il ramo supporta osservabilita shadow per lezioni
metacognitive senza cambiare il contesto model-facing normale.

Aggiornamento V1.23.0: `runtime_context.memory_context.conflicts` non segnala
piu' related overlap come conflitto. Questo mantiene il contesto automatico piu
pulito e impedisce che cautela/affect/debug vengano attivati da somiglianze
generiche tra memorie.

Aggiornamento V1.25.4: la percezione delle capability non deriva piu
direttamente da `MIND_API_ROUTES`. Il modello vede `interface=mind_shell`,
famiglie comando e status da registry; endpoint come
`memory.facts.backfill` restano indicati solo come
`internal_maintenance_only`.

Aggiornamento V1.26.0 planning: il prossimo salto del ramo non e aggiungere
piu blocchi al prompt, ma definire un router di context pack. Il contesto deve
restare una superficie cognitiva instradata: spine minima sempre attiva,
pack per source-sensitive/temporal/project/emotional work, e futuri pack
embodied per sensori e attuatori.

Aggiornamento V1.29.0: la spine sessione/memoria e attiva. Le famiglie
preservate (`recent_dialogue`, eventi recenti, capability, `scarlet_state`,
focus, affect, metacognizione) restano da discutere una per una. Le prove live
mostrano inoltre che la provider history con tool result puo superare per peso
il contesto V2 e deve entrare nella prossima progettazione di budget/modalita.

Aggiornamento V1.30.0: `context.accounting.preflight` e `observed` separano
caratteri/byte esatti, stima token, primo step e totale tool loop. Il router
modalita e attivo solo sui blocchi automatici; la shell resta disponibile on
demand. La compattazione 100k + coda desiderata di 8 turni resta non mutante
finche sessioni reali lunghe non definiscono una degradazione sicura.

Aggiornamento V1.35.0: `preserved_context` non e piu una zona di compatibilita.
Il proiettore copia solo campi cognitivamente utilizzabili di focus, affect e
metacognizione quando i relativi modi li rendono model-facing. Il rich runtime
resta completo per sistema/UI/trace. `scarlet_state`, `recent_dialogue`, eventi
generici e capability automatiche sono esclusi; provider history e comandi
dedicati restano le fonti corrette. MiniMax e GPT ricevono lo stesso documento
V2 canonico.

Aggiornamento V1.36.0: la cronologia provider resta canonica e append-only, ma
ogni turno completo puo ora essere mappato alla sua slice esatta con ids di
messaggi, tool e trace. Il piano shadow usa aree token `O/C/H/A/M`, non otto
turni fissi. `C` e `H` hanno massimali normali da 100k, la sicurezza riserva
25k e `A` assorbe il resto sotto 500k. Un turno singolo oltre `H` resta intero
se entra nella finestra fisica da 1M; oltre 1M il piano fallisce chiuso.

Aggiornamento V1.39.0: la compattazione cronologica e attiva sul runtime nativo
in modalita protetta. Gli artifact ricorsivi sono append-only e source-labelled;
la richiesta al modello usa `cronologia compattata + coda canonica esatta +
messaggio corrente`, mentre persistenza e audit continuano a usare la storia
canonica completa. Artifact mancanti, stale o non mappabili producono fallback
esplicito alla cronologia canonica.

Aggiornamento V1.58.0: la futura percezione periferica viene esplorata prima in
un ledger tecnico append-only. L'esistenza di un dato sul device non implica
utilita cognitiva: ammissione, sintesi, frequenza e routing saranno progettati
solo dopo osservazioni fisiche e valutazione umana/LLM dei payload reali.

Aggiornamento V1.59.0: il ramo possiede un contratto tipizzato per
classificare i futuri segnali prima della loro ammissione. Il router e
shadow-only e aggiunge una receipt non model-facing al trace `model.context`;
il ledger Device Exploration resta completamente isolato. La distinzione
`subject_domain`/`observer_domain` impedisce di attribuire a Scarlet sensori del
telefono o di trattare il GPS del device come prova diretta della posizione
umana.

Aggiornamento V1.60.0: le attivazioni autonome ricevono un pack compatto
separato dal turno umano, con disponibilita percettiva navigabile. I payload
esatti entrano nel ciclo solo dopo apertura esplicita; trace, lease, diagnostica
e dati raw non aperti restano sistemici.

Aggiornamento V1.61.0: il pack autonomo separato e stato ritirato. Turni umani
e attivazioni autonome usano lo stesso `scarlet-model-context-v2`, lo stesso
retrieve/rerank automatico, gli stessi organi e la stessa shell. Restano
separate soltanto le cronologie provider e la provenienza deterministica. Il
pack sessione umano include sempre un hint navigabile della cronologia
autonoma; memorie automatiche e risultati shell dichiarano origine, kind
sessione, trigger, attore e ruolo messaggio. `perception` indica ora
esplicitamente soltanto osservazioni esterne e non va usato per cercare cicli
interni, sessioni o memoria.

## Sviluppi precedenti

- Memory Context Pipeline v0.
- Runtime context stratificato.
- Temporal context con clock unico.
- Platform language configurata.
- Profilo, privacy e locale operativi.
- Recent runtime events nel turno successivo.
- V1.6.0: registro blocchi runtime/model/UI e inspector `Modello` per verificare
  ordine, contenuto e ridondanze dei dati inviati al modello.
- V1.7.0: lifecycle UI dei blocchi streaming con riconciliazione live/persisted
  a fine turno.
- V1.7.1: prompt fix per trattare i blocchi runtime/memory gia iniettati come
  evidenza sufficiente nei turni contestuali semplici.
- V1.9.0: `metacognitive.context` shadow e rendering UI dedicato per valutare
  trigger/lezioni candidate prima di attivare retrieval metacognitivo reale.
- V1.26.0 planning: baseline documentale per context pack, classificazione
  organi/fonti/capacita, degradazione sotto budget e shadow router futuro.

## Verifica V1.39.0

- Implementazione: compilatore V2 condiviso, proiettore preservato con
  allowlist, exact `model.context`, audit field-level, tempo utente unico,
  session/memory hook compatti e provenienza navigabile.
- Test deterministici: contratti V2, allowlist ed esclusioni, deduplica,
  timezone, summary fallback, GPT parity e mode routing.
- Evidenza Scarlet: probe nativo e GPT riusciti; memoria e tempo V2 usati
  correttamente.
- Integrazione runtime: V2 e router automatico `interactive` attivi;
  accounting e compattazione cronologica derivata attivi, con fallback
  canonico condiviso tra sync e streaming.
- Calibrazione cronologica: tre sessioni reali lette senza mutazione e confronto
  bounded full/derived su due; il caso normale ha ridotto input e latenza, il
  caso da 340k ha validato l'eccezione whole-turn.
- Verifica diretta V1.39: due generazioni MiniMax ricorsive su copia disposable
  di una sessione da circa 350k token; richiamo corretto dal prefisso compattato,
  coda esatta preservata e nessuna mutazione canonica.
- Prossimo gate: monitorare qualita multi-ciclo, fedelta delle fonti e taratura
  delle partizioni prima di modificarne i massimali.

## Evolutive

- Calibrare i tag del registry gia attivo senza ampliare implicitamente le
  allowlist model-facing.
- Monitorare la vista cronologica derivata su ulteriori sessioni lunghe senza
  perdere continuita semantica, tool evidence o cronologia canonica.
- Sostituire eventuali responsabilita residue di `scarlet_state` con organi o
  comandi dedicati, senza reiniettare il blocco legacy.
- Separare dati sessione, dati messaggio, dati utente e dati ambiente con
  policy ancora piu esplicite.
- Aggiungere contesto ambiente reale quando esisteranno operativita esterne.
- Aggiungere receipt/evidence id per ogni blocco percepito.
- Valutare quali blocchi aiutano davvero il routing dello sforzo e quali
  rischiano di spingere M3 verso analisi eccessive.
- Per embodiment futuro, inviare al modello sintesi di scena/audio/azione e
  non stream sensoriali raw, con pack attuativi sempre gated da sicurezza.
