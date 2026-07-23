import { Braces } from "lucide-react";

export function DataJsonPanel({
  compact = false,
  data,
  title
}: {
  compact?: boolean;
  data: unknown;
  title: string;
}) {
  return (
    <section
      className={`scarlet-data-json${compact ? " is-compact" : ""}`}
      data-testid="data-json-panel"
    >
      <header>
        <span><Braces aria-hidden="true" size={15} /></span>
        <div>
          <p>Dati disponibili</p>
          <h2>{title}</h2>
        </div>
        <small>fixture locale</small>
      </header>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </section>
  );
}
