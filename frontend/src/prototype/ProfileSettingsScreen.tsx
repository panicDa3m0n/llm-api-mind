import {
  ArchiveRestore,
  Download,
  FlaskConical,
  Globe2,
  LogOut,
  Save,
  Settings2,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  Wrench
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { updateRuntimeSettings } from "../api";
import type { RuntimeSettings, UserProfile } from "../types";
import { DataJsonPanel } from "./DataJsonPanel";
import type { UnavailableFeature } from "./UnavailableFeatureModal";

type SettingsDraft = {
  country_code: string;
  language: string;
  privacy_scope: string;
  timezone: string;
  user_display_name: string;
};

export function ProfileSettingsScreen({
  onLogout,
  onPrivateEvidenceChange,
  onSettingsChanged,
  onUnavailable,
  privateEvidenceUnlocked,
  profile,
  settings,
  username
}: {
  onLogout: () => void;
  onPrivateEvidenceChange: (unlocked: boolean) => void;
  onSettingsChanged: (settings: RuntimeSettings) => void;
  onUnavailable: (feature: UnavailableFeature) => void;
  privateEvidenceUnlocked: boolean;
  profile: UserProfile | null;
  settings: RuntimeSettings | null;
  username: string;
}) {
  const [draft, setDraft] = useState<SettingsDraft>(() => settingsDraft(settings, username));
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("I campi disponibili sono collegati al Core.");

  useEffect(() => {
    setDraft(settingsDraft(settings, username));
  }, [settings, username]);

  async function saveSettings() {
    if (!settings || saving) return;
    setSaving(true);
    setFeedback("Salvataggio nel Core…");
    try {
      const updated = await updateRuntimeSettings(draft);
      onSettingsChanged(updated);
      setFeedback("Impostazioni salvate nel Core.");
    } catch (error) {
      setFeedback(
        error instanceof Error ? error.message : "Salvataggio non riuscito."
      );
    } finally {
      setSaving(false);
    }
  }

  function unavailable(label: string, detail?: string) {
    onUnavailable({ label, detail });
  }

  const settingsData = {
    profile,
    runtime_settings: settings,
    local_interface: {
      private_evidence_unlocked: privateEvidenceUnlocked,
      storage: "local device preference",
      provider_thinking_text:
        privateEvidenceUnlocked ? "visible in development" : "hidden by user"
    },
    editable_contract: [
      "user_display_name",
      "language",
      "country_code",
      "timezone",
      "privacy_scope"
    ],
    unavailable_in_core: [
      "account_registration",
      "account_deletion",
      "privacy_export",
      "notifications",
      "voice",
      "avatar_preferences",
      "consumer_maintenance"
    ]
  };

  return (
    <section className="scarlet-screen scarlet-settings" data-testid="profile-screen">
      <div className="scarlet-settings__surface">
        <header className="scarlet-settings__top">
          <div>
            <p><Settings2 aria-hidden="true" size={14} /> Impostazioni</p>
            <h1>Il tuo spazio, le tue regole.</h1>
            <span>Solo i controlli già supportati modificano il sistema reale.</span>
          </div>
          <button
            aria-label="Esci"
            className="scarlet-settings__logout"
            onClick={onLogout}
            type="button"
          >
            <LogOut aria-hidden="true" size={16} /><span>Esci</span>
          </button>
        </header>

        <section className="scarlet-settings__group">
          <GroupTitle
            detail="Identità e ambiente persistiti nelle runtime preferences."
            icon={<UserRound aria-hidden="true" size={17} />}
            title="Profilo e ambiente"
          />
          <div className="scarlet-settings__identity">
            <span><UserRound aria-hidden="true" size={25} /></span>
            <div>
              <small>Profilo Core</small>
              <strong>{profile?.display_name || username}</strong>
              <p>
                {profile
                  ? `${profile.language_label} · ${profile.timezone} · ${profile.memory_count} ricordi`
                  : "Profilo in caricamento"}
              </p>
            </div>
          </div>
          <div className="scarlet-settings__form-grid">
            <label>
              <span>Nome visualizzato</span>
              <input
                disabled={!settings}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    user_display_name: event.target.value
                  }))
                }
                value={draft.user_display_name}
              />
            </label>
            <SettingsSelect
              disabled={!settings}
              icon={<Globe2 aria-hidden="true" size={14} />}
              label="Lingua"
              onChange={(value) => setDraft((current) => ({ ...current, language: value }))}
              options={settings?.options.languages.map((item) => ({
                label: item.label,
                value: item.code
              })) ?? []}
              value={draft.language}
            />
            <SettingsSelect
              disabled={!settings}
              label="Paese"
              onChange={(value) => setDraft((current) => ({ ...current, country_code: value }))}
              options={settings?.options.countries.map((item) => ({
                label: item.label,
                value: item.code
              })) ?? []}
              value={draft.country_code}
            />
            <SettingsSelect
              disabled={!settings}
              label="Fuso orario"
              onChange={(value) => setDraft((current) => ({ ...current, timezone: value }))}
              options={settings?.options.timezones.map((item) => ({
                label: item.label,
                value: item.id
              })) ?? []}
              value={draft.timezone}
            />
          </div>
        </section>

        <section className="scarlet-settings__group">
          <GroupTitle
            detail="Queste preferenze richiedono ancora un contratto di composizione prompt."
            icon={<Sparkles aria-hidden="true" size={17} />}
            title="Comportamento di Scarlet"
          />
          <div className="scarlet-settings__preferences">
            {[
              ["Risposte concise", "Riduce preamboli e mantiene le risposte dirette."],
              ["Note di contesto", "Rende visibile quando Scarlet usa memoria e continuità."],
              ["Iniziativa controllata", "Scarlet può proporre il prossimo passo utile."],
              ["Tono relazionale", "Mantiene una voce calda, personale e collaborativa."],
              ["Notifiche", "Avvisi web e Android per attività completate."]
            ].map(([label, detail]) => (
              <PreferenceRow
                detail={detail}
                key={label}
                label={label}
                onClick={() => unavailable(label)}
              />
            ))}
          </div>
          <div className="scarlet-settings__save">
            <button
              disabled={!settings || saving}
              onClick={() => void saveSettings()}
              type="button"
            >
              <Save aria-hidden="true" size={15} />
              {saving ? "Salvataggio…" : "Salva profilo e ambiente"}
            </button>
            <p aria-live="polite">{feedback}</p>
          </div>
        </section>

        <section className="scarlet-settings__group">
          <GroupTitle
            detail="L’ambito memoria è reale; gli altri workflow non esistono ancora."
            icon={<ShieldCheck aria-hidden="true" size={17} />}
            title="Privacy e dati"
          />
          <div className="scarlet-settings__privacy-row">
            <SettingsSelect
              disabled={!settings}
              label="Ambito privacy"
              onChange={(value) =>
                setDraft((current) => ({ ...current, privacy_scope: value }))
              }
              options={settings?.options.privacy_scopes.map((item) => ({
                label: item.label,
                value: item.id
              })) ?? []}
              value={draft.privacy_scope}
            />
          </div>
          <div className="scarlet-settings__preferences">
            <PreferenceRow
              active={privateEvidenceUnlocked}
              detail="Mostra thinking ed evidenze diagnostiche ricevute dal Core. È attivo di default durante lo sviluppo."
              label="Evidenze di sviluppo"
              onClick={() =>
                onPrivateEvidenceChange(!privateEvidenceUnlocked)
              }
            />
          </div>
          <div className="scarlet-settings__command-grid">
            <SettingsCommand
              detail="Il Core non espone ancora un archivio privacy."
              icon={<Download aria-hidden="true" size={16} />}
              label="Esporta dati"
              onClick={() => unavailable("Esporta dati")}
            />
            <SettingsCommand
              danger
              detail="Non esiste ancora un account server da eliminare."
              icon={<Trash2 aria-hidden="true" size={16} />}
              label="Elimina account"
              onClick={() => unavailable("Elimina account")}
            />
          </div>
        </section>

        <section className="scarlet-settings__group">
          <GroupTitle
            detail="Le API operative non vengono esposte come comandi consumer."
            icon={<Wrench aria-hidden="true" size={17} />}
            title="Manutenzione ed extra"
          />
          <div className="scarlet-settings__command-grid">
            <SettingsCommand
              detail="Richiede un futuro workflow consumer protetto."
              icon={<Wrench aria-hidden="true" size={16} />}
              label="Controlla memoria"
              onClick={() => unavailable("Controlla memoria")}
            />
            <SettingsCommand
              detail="Il Core non espone archiviazione sessioni consumer."
              icon={<ArchiveRestore aria-hidden="true" size={16} />}
              label="Rivedi sessioni"
              onClick={() => unavailable("Rivedi sessioni")}
            />
            <SettingsCommand
              detail="Voce e promemoria non sono ancora implementati."
              icon={<FlaskConical aria-hidden="true" size={16} />}
              label="Funzioni sperimentali"
              onClick={() => unavailable("Funzioni sperimentali")}
            />
            <SettingsCommand
              detail="Il catalogo statico non ha ancora preferenze runtime."
              icon={<Sparkles aria-hidden="true" size={16} />}
              label="Stati di Scarlet"
              onClick={() => unavailable("Stati di Scarlet")}
            />
          </div>
        </section>
      </div>

      <DataJsonPanel data={settingsData} title="Profilo e regole runtime" />
    </section>
  );
}

function settingsDraft(
  settings: RuntimeSettings | null,
  username: string
): SettingsDraft {
  return {
    country_code: settings?.country_code ?? "",
    language: settings?.language ?? "",
    privacy_scope: settings?.privacy_scope ?? "",
    timezone: settings?.timezone ?? "",
    user_display_name: settings?.user_display_name ?? username
  };
}

function GroupTitle({
  detail,
  icon,
  title
}: {
  detail: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <header className="scarlet-settings__group-title">
      <span>{icon}</span>
      <div><h2>{title}</h2><p>{detail}</p></div>
    </header>
  );
}

function PreferenceRow({
  active = false,
  detail,
  label,
  onClick
}: {
  active?: boolean;
  detail: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={active}
      className="scarlet-profile-screen__preference"
      onClick={onClick}
      type="button"
    >
      <span><strong>{label}</strong><small>{detail}</small></span>
      <i aria-hidden="true" className={active ? "is-on" : ""}>
        <b />
      </i>
    </button>
  );
}

function SettingsSelect({
  disabled,
  icon,
  label,
  onChange,
  options,
  value
}: {
  disabled: boolean;
  icon?: ReactNode;
  label: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  value: string;
}) {
  return (
    <label>
      <span>{icon}{label}</span>
      <select
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.length === 0 ? <option value="">Non disponibile</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

function SettingsCommand({
  danger = false,
  detail,
  icon,
  label,
  onClick
}: {
  danger?: boolean;
  detail: string;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={danger ? "is-danger" : ""} onClick={onClick} type="button">
      <span>{icon}</span>
      <div><strong>{label}</strong><small>{detail}</small></div>
    </button>
  );
}
