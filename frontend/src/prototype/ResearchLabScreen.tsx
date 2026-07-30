import {
  ArrowLeft,
  Download,
  FileCode2,
  FileJson2,
  FileSpreadsheet,
  FileText,
  FlaskConical,
  Image as ImageIcon,
  LoaderCircle,
  RefreshCw,
  Trash2,
  TriangleAlert
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  deleteResearchLabArtifact,
  fetchResearchLabArtifactContent
} from "../api";
import type {
  DashboardResearchLab,
  ResearchLabArtifact,
  ResearchLabRun
} from "../types";
import "./research-lab.css";

type ArtifactPreview = {
  text: string | null;
  url: string | null;
  error: string | null;
  loading: boolean;
};

const EMPTY_PREVIEW: ArtifactPreview = {
  text: null,
  url: null,
  error: null,
  loading: false
};

export function ResearchLabScreen({
  data,
  loading,
  onBack,
  onRefresh,
  onArtifactDeleted
}: {
  data: DashboardResearchLab | null;
  loading: boolean;
  onBack: () => void;
  onRefresh: () => void;
  onArtifactDeleted: () => void;
}) {
  const artifacts = useMemo(
    () => data?.runs.flatMap((run) => run.artifacts) ?? [],
    [data]
  );
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [preview, setPreview] = useState<ArtifactPreview>(EMPTY_PREVIEW);
  const [deletingArtifactId, setDeletingArtifactId] = useState<string | null>(null);

  const selectedArtifact =
    artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  useEffect(() => {
    if (selectedArtifactId && !selectedArtifact) {
      setSelectedArtifactId(null);
    }
  }, [selectedArtifact, selectedArtifactId]);

  useEffect(() => {
    if (!selectedArtifact) {
      setPreview(EMPTY_PREVIEW);
      return;
    }

    let active = true;
    let objectUrl: string | null = null;
    setPreview({ text: null, url: null, error: null, loading: true });
    void fetchResearchLabArtifactContent(selectedArtifact.id)
      .then(async (blob) => {
        if (!active) return;
        const kind = previewKind(selectedArtifact);
        if (kind === "text") {
          const raw = await blob.text();
          if (!active) return;
          setPreview({
            text: formatTextArtifact(raw, selectedArtifact.media_type),
            url: null,
            error: null,
            loading: false
          });
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setPreview({ text: null, url: objectUrl, error: null, loading: false });
      })
      .catch((error) => {
        if (!active) return;
        setPreview({
          text: null,
          url: null,
          error: error instanceof Error ? error.message : "Impossibile aprire il file.",
          loading: false
        });
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedArtifact]);

  async function removeArtifact(artifact: ResearchLabArtifact) {
    const accepted = window.confirm(
      `Eliminare “${artifact.name}”? La ricevuta della sua elaborazione resterà disponibile.`
    );
    if (!accepted) return;
    setDeletingArtifactId(artifact.id);
    try {
      await deleteResearchLabArtifact(artifact.id);
      if (selectedArtifactId === artifact.id) setSelectedArtifactId(null);
      onArtifactDeleted();
    } finally {
      setDeletingArtifactId(null);
    }
  }

  return (
    <section className="scarlet-lab" aria-labelledby="research-lab-title">
      <header className="scarlet-lab__header">
        <button className="scarlet-lab__back" onClick={onBack} type="button">
          <ArrowLeft aria-hidden="true" size={17} />
          Dashboard
        </button>
        <button
          aria-label="Aggiorna laboratorio"
          className="scarlet-lab__refresh"
          disabled={loading}
          onClick={onRefresh}
          title="Aggiorna"
          type="button"
        >
          <RefreshCw aria-hidden="true" size={17} />
        </button>
      </header>

      <div className="scarlet-lab__hero">
        <span aria-hidden="true"><FlaskConical size={22} /></span>
        <div>
          <p>Ricerca e calcolo</p>
          <h1 id="research-lab-title">Laboratorio di Scarlet</h1>
          <small>
            {data?.enabled && data.runner_configured
              ? "Le elaborazioni e i file che Scarlet ha scelto di conservare."
              : "Il laboratorio non è disponibile in questa configurazione."}
          </small>
        </div>
      </div>

      <div className="scarlet-lab__content">
        <section className="scarlet-lab__runs" aria-label="Elaborazioni recenti">
          <div className="scarlet-lab__section-title">
            <div>
              <p>Attività</p>
              <h2>Elaborazioni recenti</h2>
            </div>
            <strong>{loading ? "…" : String(data?.total ?? 0)}</strong>
          </div>
          {loading ? <LabEmpty text="Apro il laboratorio…" /> : null}
          {!loading && !data?.runs.length ? (
            <LabEmpty text="Scarlet non ha ancora conservato alcun artefatto." />
          ) : null}
          {data?.runs.map((run) => (
            <RunCard
              deletingArtifactId={deletingArtifactId}
              key={run.id}
              onDelete={removeArtifact}
              onOpen={setSelectedArtifactId}
              run={run}
              selectedArtifactId={selectedArtifactId}
            />
          ))}
        </section>

        <section className="scarlet-lab__preview" aria-live="polite">
          {selectedArtifact ? (
            <ArtifactPreview artifact={selectedArtifact} preview={preview} />
          ) : (
            <LabEmpty text="Scegli un file per leggerlo qui." />
          )}
        </section>
      </div>
    </section>
  );
}

function RunCard({
  deletingArtifactId,
  onDelete,
  onOpen,
  run,
  selectedArtifactId
}: {
  deletingArtifactId: string | null;
  onDelete: (artifact: ResearchLabArtifact) => void;
  onOpen: (artifactId: string) => void;
  run: ResearchLabRun;
  selectedArtifactId: string | null;
}) {
  const stdout = typeof run.result.stdout === "string" ? run.result.stdout.trim() : "";
  const stderr = typeof run.result.stderr === "string" ? run.result.stderr.trim() : "";

  return (
    <article className="scarlet-lab__run">
      <header>
        <span className={`scarlet-lab__status is-${run.status}`}>
          {run.status === "completed" ? "Completata" : "Non completata"}
        </span>
        <time dateTime={run.started_at}>{formatDate(run.started_at)}</time>
      </header>
      <h3>{run.action === "python" ? "Elaborazione" : "Fonte consultata"}</h3>
      <p>{run.intent}</p>
      {stdout ? <pre className="scarlet-lab__output">{stdout}</pre> : null}
      {stderr ? <p className="scarlet-lab__error">{stderr}</p> : null}
      {run.artifacts.length ? (
        <div className="scarlet-lab__artifact-list">
          {run.artifacts.map((artifact) => (
            <div className="scarlet-lab__artifact" key={artifact.id}>
              <button
                aria-pressed={selectedArtifactId === artifact.id}
                className={selectedArtifactId === artifact.id ? "is-selected" : ""}
                onClick={() => onOpen(artifact.id)}
                type="button"
              >
                <ArtifactIcon artifact={artifact} />
                <span><strong>{artifact.name}</strong><small>{formatBytes(artifact.byte_size)}</small></span>
              </button>
              <button
                aria-label={`Elimina ${artifact.name}`}
                className="scarlet-lab__delete"
                disabled={deletingArtifactId === artifact.id}
                onClick={() => onDelete(artifact)}
                title="Elimina artefatto"
                type="button"
              >
                {deletingArtifactId === artifact.id ? (
                  <LoaderCircle aria-hidden="true" size={16} />
                ) : <Trash2 aria-hidden="true" size={16} />}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function ArtifactPreview({
  artifact,
  preview
}: {
  artifact: ResearchLabArtifact;
  preview: ArtifactPreview;
}) {
  const kind = previewKind(artifact);
  return (
    <>
      <header className="scarlet-lab__preview-header">
        <div><ArtifactIcon artifact={artifact} /><span><strong>{artifact.name}</strong><small>{artifact.media_type}</small></span></div>
        {preview.url ? (
          <a download={artifact.name} href={preview.url} title="Scarica artefatto">
            <Download aria-hidden="true" size={17} />
          </a>
        ) : null}
      </header>
      {preview.loading ? <LabEmpty text="Preparo l’artefatto…" /> : null}
      {preview.error ? (
        <p className="scarlet-lab__error"><TriangleAlert aria-hidden="true" size={16} /> {preview.error}</p>
      ) : null}
      {!preview.loading && !preview.error && kind === "text" ? (
        <pre className="scarlet-lab__file-text">{preview.text}</pre>
      ) : null}
      {!preview.loading && !preview.error && kind === "image" && preview.url ? (
        <img alt={artifact.name} className="scarlet-lab__image" src={preview.url} />
      ) : null}
      {!preview.loading && !preview.error && kind === "pdf" && preview.url ? (
        <iframe className="scarlet-lab__pdf" src={preview.url} title={artifact.name} />
      ) : null}
      {!preview.loading && !preview.error && kind === "download" && preview.url ? (
        <a className="scarlet-lab__download" download={artifact.name} href={preview.url}>
          <Download aria-hidden="true" size={18} /> Scarica per aprire
        </a>
      ) : null}
    </>
  );
}

function ArtifactIcon({ artifact }: { artifact: ResearchLabArtifact }) {
  const kind = previewKind(artifact);
  if (kind === "image") return <ImageIcon aria-hidden="true" size={18} />;
  if (artifact.media_type.includes("json")) return <FileJson2 aria-hidden="true" size={18} />;
  if (artifact.media_type.includes("csv") || artifact.name.match(/\.(csv|tsv)$/i)) {
    return <FileSpreadsheet aria-hidden="true" size={18} />;
  }
  if (kind === "text") return <FileText aria-hidden="true" size={18} />;
  return <FileCode2 aria-hidden="true" size={18} />;
}

function LabEmpty({ text }: { text: string }) {
  return <p className="scarlet-lab__empty">{text}</p>;
}

function previewKind(artifact: ResearchLabArtifact): "text" | "image" | "pdf" | "download" {
  const mediaType = artifact.media_type.toLowerCase();
  if (
    mediaType.startsWith("text/") ||
    mediaType.includes("json") ||
    artifact.name.match(/\.(csv|tsv|log|md|py|txt|json)$/i)
  ) return "text";
  if (mediaType.startsWith("image/")) return "image";
  if (mediaType === "application/pdf" || artifact.name.endsWith(".pdf")) return "pdf";
  return "download";
}

function formatTextArtifact(value: string, mediaType: string): string {
  if (!mediaType.includes("json")) return value;
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "data non disponibile";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
