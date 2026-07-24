import { Construction, X } from "lucide-react";
import { useEffect, useRef } from "react";

export type UnavailableFeature = {
  label: string;
  detail?: string;
};

export function UnavailableFeatureModal({
  feature,
  onClose
}: {
  feature: UnavailableFeature | null;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!feature) return;
    closeRef.current?.focus();
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [feature, onClose]);

  if (!feature) return null;

  return (
    <div
      aria-labelledby="unavailable-title"
      aria-modal="true"
      className="scarlet-unavailable"
      data-testid="unavailable-modal"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
      role="dialog"
    >
      <section className="scarlet-unavailable__dialog">
        <button
          aria-label="Chiudi"
          className="scarlet-unavailable__close"
          onClick={onClose}
          ref={closeRef}
          type="button"
        >
          <X aria-hidden="true" size={18} />
        </button>
        <span className="scarlet-unavailable__icon" aria-hidden="true">
          <Construction size={22} />
        </span>
        <p>{feature.label}</p>
        <h2 id="unavailable-title">Funzione non disponibile</h2>
        <span>
          {feature.detail ??
            "Questa funzione non è ancora presente nel sistema reale di Scarlet."}
        </span>
        <button
          className="scarlet-unavailable__confirm"
          onClick={onClose}
          type="button"
        >
          Ho capito
        </button>
      </section>
    </div>
  );
}
