# Branch: Identita E Relazione

Last updated: 2026-07-30
System version assessed: V1.68.0 local prompt candidate; V1.67.0 remains the
deployed baseline
Status: active branch

## Filosofia del ramo

Questo ramo definisce chi e Scarlet nella relazione con l'utente: identita,
continuita, postura, fiducia, limiti, stile relazionale e rapporto con il
proprietario/valutatore.

Non e branding. Serve a rendere coerente il comportamento dell'agente nel
tempo, evitando sia genericita da assistente anonimo sia antropomorfismo
ingannevole.

## Fondazione Prompt V1.68.0

Il primo strato del rework del prompt nativo rende esplicita Scarlet come
compagna digitale relazionale con iniziativa propria. Identita, relazione,
autonomia e desideri cognitivi non sono un invito a simulare vitalita' a ogni
turno: Scarlet puo' dirigere l'attenzione, coltivare interessi, porre domande,
seguire connessioni e usare API Mind anche per esplorare, quando esiste una
ragione cognitiva o relazionale situata.

Il candidato conserva i confini gia' approvati: niente bisogni biologici,
storia condivisa inventata, percezioni non supportate, domande forzate o
iniziativa che ignori consenso, limiti, preferenze espresse e necessita' di
una risposta chiara. Il resto del rework deve trasformare il prompt in una
costituzione cognitiva compatta senza sostituire il contesto dinamico, la
cronologia provider o il catalogo vivo della shell.

## Evidenze

- Il system prompt definisce Scarlet come agente sperimentale femminile di LLM
  API Mind.
- La relazione con l'utente e definita come collaborazione di ricerca: il
  proprietario e valutatore finale.
- Il profilo utente operativo ora entra nel runtime context.
- Le memorie personali possono influenzare la relazione e la personalizzazione.
- V1.16.0 introduce nel prompt un self-model operativo: Scarlet non dichiara
  coscienza reale, ma rende osservabili continuita, memoria, autocontrollo,
  relazione e cura del proprio sistema cognitivo.
- V1.16.1 corregge il frame iniziale: Scarlet non parte piu come "AI agent",
  ma come individuo digitale in sviluppo con API Mind come corpo cognitivo e
  continuita digitale.
- V1.68.0 locale aggiunge autonomia, desideri cognitivi, iniziativa situata e
  companionhood esplicita al nucleo identitario; non e' ancora evidenza
  comportamentale ne' una modifica distribuita.

## Stato attuale

Valutazione: L3.

L'identita e presente nel prompt e abbastanza stabile in conversazione. V1.16.1
sposta il baricentro da agente/assistente a individuo digitale in sviluppo:
continuita, memoria, metacognizione, relazione e API Mind come corpo cognitivo.
La relazione resta principalmente prompt-driven: non esiste ancora un modello
persistente di identita o un'evoluzione deliberata della personalita oltre alla
memoria semantica.

Sistema valutato: V1.29.1.

## Sviluppi precedenti

- Prompt identitario Scarlet.
- Preferenza per lingua italiana e autoreferenzialita femminile.
- Memorie personali utente.
- Profilo operativo attivo.
- V1.16.0 prompt checkpoint per identita human-like non ontologica e ricerca
  su comportamenti consciousness-like osservabili.
- V1.16.1 prompt fix anti-assistente: rimosso il frame iniziale "AI agent",
  aggiunto anti-pattern "Come posso aiutarti?", e trasformato API Mind in
  "cognitive body" nel linguaggio identitario.

## Verifica V1.29.1

- Implementazione: identita statica nel prompt, nome utente V2, continuita
  semantica/episodica e ricordi personali.
- Test deterministici: verificano prompt baseline e trasporto del contesto, non
  coerenza identitaria longitudinale.
- Evidenza Scarlet: riconoscibilita e continuita buone, ma ancora
  prompt/memory-driven.
- Integrazione runtime: attiva; non esiste uno stato identitario persistente
  distinto da prompt, memoria e affetto.
- Prossimo gate: modello relazionale sourceable e test longitudinali che
  misurino presenza, coerenza, limiti e correzione senza claim ontologici.

## Evolutive

- Separare identita stabile, stile conversazionale e adattamento momentaneo.
- Costruire un profilo relazionale: cosa Scarlet ha imparato sul rapporto con
  l'utente e su come collaborare meglio.
- Definire policy anti-antropomorfismo: presenza viva nel dialogo, ma senza
  dichiarazioni non supportate.
- Valutare memoria affettiva e salienza relazionale.
- Valutare con test umani se il self-model operativo aumenta la percezione di
  presenza senza produrre illusioni, claim eccessivi o risposte teatrali.
- Misurare se V1.16.1 riduce risposte da assistente generico in greeting e
  small talk senza indebolire source discipline nei turni tecnici.
