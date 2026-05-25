# Branch: Metacognizione

Last updated: 2026-05-25  
System version assessed: V1.0.1  
Status: experimental branch

## Filosofia del ramo

La metacognizione deve permettere a Scarlet di ragionare sul proprio
ragionamento: verificare assunzioni, criticare bozze, cercare evidenze
mancanti, riconoscere conflitti, decidere se continuare a pensare o rispondere.

Non deve essere fittizia, decorativa o composta da endpoint duplicati. Il ramo
deve puntare a vera utilita nel risultato finale.

## Evidenze

- Esiste un unico endpoint LLM-backed:
  `POST /mind/metacognition/step`.
- Il prompt indica quando usarlo per task complessi, sensibili o incerti.
- Le route parallele di reflection/blackboard/validation sono state rimosse
  per evitare caos.
- Evidenza live ancora insufficiente: Scarlet non invoca sempre la
  metacognizione quando dovrebbe.

## Stato attuale

Valutazione: L2/L3.

Tecnicamente implementata come prototipo tracciabile. Comportamentalmente non
ancora validata. Il ramo non deve espandersi in molti endpoint finche il singolo
percorso non dimostra limiti reali misurati.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Rimozione della metacognizione visiva fittizia.
- Introduzione delle public work notes.
- Unificazione su `/mind/metacognition/step`.
- Scripted test per schema, alias e JSON repair.

## Evolutive

- Prompt reviewer per modalita: verifica fonti, conflitti memoria, decisione
  progettuale, risposta emotiva, task tecnico.
- Continuation loop quando `should_continue=true`.
- Tracce di miglioramento: confronto risposta pre/post metacognizione.
- Trigger automatici basati su rischio, incertezza, conflitto o claim forte.
