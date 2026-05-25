# Branch: Comunicazione Agente-Utente

Last updated: 2026-05-25  
System version assessed: V1.0.1  
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
- Le prove live hanno mostrato che Scarlet puo usare runtime context e memoria
  senza chiamate tool quando l'evidenza e gia sufficiente.
- Punto aperto: le note agentiche naturali sono presenti via prompt, ma non sono
  ancora equivalenti alla fluidita di agenti IDE maturi come Codex/Claude Code.

## Stato attuale

Valutazione: L3/L4.

La comunicazione base e buona. Scarlet ha una voce riconoscibile, risponde in
italiano per default, puo dichiarare l'evidenza usata e la UI rende il turno
abbastanza leggibile. Il ramo non e ancora L5 perche il comportamento agentico
intermedio non e sempre naturale, coerente o proporzionato al lavoro in corso.

Sistema valutato: V1.0.1.

## Sviluppi precedenti

- Identita Scarlet e prompt di base.
- Rimozione della vecchia metacognizione visiva fittizia.
- Introduzione delle public work notes.
- Rework UI per mostrare blocchi di runtime, memorie, tool e risposta finale in
  modo umano.
- Runtime settings per lingua piattaforma, default italiano.

## Evolutive

- Definire un protocollo di note pubbliche piu calibrato: breve per task
  semplici, piu ricco per task investigativi.
- Rendere le note parte utile della memoria episodica senza trasformarle in
  rumore.
- Studiare modalita comunicative: laboratorio tecnico, conversazione personale,
  debug, decisione progettuale, report.
- Valutare se la UI debba distinguere "nota di lavoro", "evidenza", "decisione"
  e "risposta finale" come blocchi separati.
