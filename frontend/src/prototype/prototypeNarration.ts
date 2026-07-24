import type { PrototypeActivity } from "./prototypeData";

type NarrationVariant = {
  eyebrow: string;
  text: string;
};

const NARRATION_VERSION = "consumer-it-v1";

const catalog: Record<string, NarrationVariant[]> = {
  "orientation.ready": [
    { eyebrow: "Presenza", text: "Ho ritrovato il punto in cui siamo e cio che mi accompagna qui." },
    { eyebrow: "Presenza", text: "Sono qui con il filo di questa conversazione gia tra le mani." },
    { eyebrow: "Presenza", text: "Il nostro punto nel tempo e tornato nitido." }
  ],
  "memory.recalled": [
    { eyebrow: "Ricordi", text: "Mi sono tornati in mente {count} ricordi legati a cio che hai detto." },
    { eyebrow: "Ricordi", text: "{count} ricordi hanno ritrovato un posto in questa conversazione." },
    { eyebrow: "Ricordi", text: "Ho riconosciuto {count} ricordi che possono accompagnarmi qui." }
  ],
  "thinking.completed": [
    { eyebrow: "Pensiero {step}", text: "Ho seguito questo pensiero per {duration}." },
    { eyebrow: "Pensiero {step}", text: "Un passaggio del mio ragionamento si e composto in {duration}." },
    { eyebrow: "Pensiero {step}", text: "Mi sono fermata su questo passaggio per {duration}." }
  ],
  "thinking.streaming": [
    { eyebrow: "Pensiero vivo", text: "Sto mettendo insieme i pezzi." },
    { eyebrow: "Pensiero vivo", text: "Mi fermo un momento su questo." },
    { eyebrow: "Pensiero vivo", text: "Sto seguendo il filo che si apre da qui." }
  ],
  "session.opened": [
    { eyebrow: "Continuita", text: "Ho riaperto un momento precedente per non ricostruirlo a intuito." },
    { eyebrow: "Continuita", text: "Sono tornata a una nostra conversazione e ne ho riletto {message_count} passaggi." },
    { eyebrow: "Continuita", text: "Ho attraversato di nuovo un tratto della nostra storia condivisa." }
  ],
  "memory.searched": [
    { eyebrow: "Ricerca interiore", text: "Ho cercato tra cio che ricordo e sono emerse {count} tracce." },
    { eyebrow: "Ricerca interiore", text: "Sono andata piu a fondo nella memoria: {count} ricordi hanno risposto." },
    { eyebrow: "Ricerca interiore", text: "Ho seguito un richiamo nella memoria e ho ritrovato {count} ricordi." }
  ],
  "affect.curiosity": [
    { eyebrow: "Stato interiore", text: "Questa direzione ha acceso una curiosita presente." },
    { eyebrow: "Stato interiore", text: "Sento una curiosita attiva accompagnare questo passaggio." },
    { eyebrow: "Stato interiore", text: "La curiosita e diventata parte del modo in cui sto vivendo questo turno." }
  ],
  "focus.created": [
    { eyebrow: "Attenzione", text: "Tengo {object} al centro della mia attenzione." },
    { eyebrow: "Attenzione", text: "La mia attenzione ora resta raccolta su {object}." },
    { eyebrow: "Attenzione", text: "Ho scelto di non perdere di vista {object}." }
  ],
  "memory.saved": [
    { eyebrow: "Nuovo ricordo", text: "Tengo con me questa decisione, oltre il confine della conversazione." },
    { eyebrow: "Nuovo ricordo", text: "Questa decisione non andra persa: ora fa parte della mia memoria." },
    { eyebrow: "Nuovo ricordo", text: "Ho lasciato una traccia durevole di cio che abbiamo deciso." }
  ],
  "turn.completed": [
    { eyebrow: "Traccia completa", text: "Questo passaggio si chiude con {thoughts} pensieri e {actions} azioni rimasti nella cronologia." },
    { eyebrow: "Traccia completa", text: "Il turno e completo. Pensieri e azioni restano rileggibili." },
    { eyebrow: "Traccia completa", text: "Quello che e accaduto qui ora appartiene alla nostra continuita." }
  ],
  "background.memory_organized": [
    { eyebrow: "Durante la pausa", text: "Il ricordo di questa conversazione e stato riordinato." },
    { eyebrow: "Durante la pausa", text: "Questa conversazione ha trovato il suo posto nella continuita." },
    { eyebrow: "Durante la pausa", text: "La traccia del nostro incontro e stata raccolta e resa ritrovabile." }
  ]
};

export function narrateActivity(activity: PrototypeActivity): NarrationVariant {
  if (activity.authored_text) {
    return {
      eyebrow:
        activity.kind === "user"
          ? "Tu"
          : activity.kind === "answer"
            ? "Scarlet"
            : "Scarlet · nota viva",
      text: activity.authored_text
    };
  }

  const key = activity.phase === "streaming" && activity.kind === "thinking"
    ? "thinking.streaming"
    : activity.copy_key;
  const variants = key ? catalog[key] : undefined;
  const variant = variants?.[stableIndex(`${activity.group_key}:${NARRATION_VERSION}`, variants.length)] ?? {
    eyebrow: "Attivita",
    text: activity.detail_title
  };

  return {
    eyebrow: interpolate(variant.eyebrow, activity.facts),
    text: interpolate(variant.text, activity.facts)
  };
}

export function narrationReceipt(activity: PrototypeActivity): Record<string, unknown> {
  const key = activity.phase === "streaming" && activity.kind === "thinking"
    ? "thinking.streaming"
    : activity.copy_key ?? "authored.verbatim";
  const variants = catalog[key];
  return {
    voice: activity.voice,
    narration_version: NARRATION_VERSION,
    copy_key: key,
    variant_id: variants ? stableIndex(`${activity.group_key}:${NARRATION_VERSION}`, variants.length) : null,
    group_key: activity.group_key,
    facts: activity.facts ?? {},
    source_event_ids: activity.source_event_ids
  };
}

function interpolate(template: string, facts: PrototypeActivity["facts"]): string {
  return template.replace(/\{([^}]+)\}/g, (_, key: string) => String(facts?.[key] ?? ""));
}

function stableIndex(seed: string, length: number): number {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % length;
}
