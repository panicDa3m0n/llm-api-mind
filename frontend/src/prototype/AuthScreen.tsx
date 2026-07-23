import { Eye, EyeOff, LockKeyhole, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";

export type AuthTab = "login" | "register";

export type AuthCredentials = {
  username: string;
  password: string;
};

export function AuthScreen({
  credentials,
  initialTab,
  onLogin,
  onRegistrationUnavailable
}: {
  credentials: AuthCredentials;
  initialTab: AuthTab;
  onLogin: (username: string) => void;
  onRegistrationUnavailable: () => void;
}) {
  const [activeTab, setActiveTab] = useState<AuthTab>(initialTab);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [registerUsername, setRegisterUsername] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerConfirmation, setRegisterConfirmation] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; message: string } | null>(null);

  function selectTab(tab: AuthTab) {
    setActiveTab(tab);
    setFeedback(null);
  }

  function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (username.trim() !== credentials.username || password !== credentials.password) {
      setFeedback({
        kind: "error",
        message: "Credenziali non riconosciute. Per il test usa scarlet / scarlet."
      });
      return;
    }

    setFeedback(null);
    onLogin(username.trim());
  }

  function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onRegistrationUnavailable();
  }

  return (
    <main className="scarlet-auth">
      <div className="scarlet-entry__signal" aria-hidden="true"><i /><i /><i /></div>
      <div className="scarlet-auth__portrait" aria-hidden="true">
        <img alt="" src="/prototype/scarlet-character-v1.png" />
      </div>

      <section className="scarlet-auth__card" aria-labelledby="scarlet-auth-title">
        <header className="scarlet-auth__header">
          <div className="scarlet-auth__avatar" aria-hidden="true">
            <img alt="" src="/prototype/scarlet-character-v1.png" />
          </div>
          <div>
            <p className="scarlet-auth__eyebrow">Il tuo spazio con Scarlet</p>
            <h1 id="scarlet-auth-title">Bentornato.</h1>
            <p>Entra nel tuo spazio privato. Gli account reali arriveranno più avanti.</p>
          </div>
        </header>

        <div className="scarlet-auth__tabs" role="tablist" aria-label="Accesso o registrazione">
          <button
            aria-controls="login-panel"
            aria-selected={activeTab === "login"}
            className={activeTab === "login" ? "is-active" : ""}
            id="login-tab"
            onClick={() => selectTab("login")}
            role="tab"
            type="button"
          >
            Login
          </button>
          <button
            aria-controls="register-panel"
            aria-selected={activeTab === "register"}
            className={activeTab === "register" ? "is-active" : ""}
            id="register-tab"
            onClick={() => selectTab("register")}
            role="tab"
            type="button"
          >
            Registrazione
          </button>
        </div>

        {activeTab === "login" ? (
          <form
            aria-labelledby="login-tab"
            className="scarlet-auth__form"
            id="login-panel"
            onSubmit={submitLogin}
            role="tabpanel"
          >
            <AuthField icon={<UserRound aria-hidden="true" size={18} />} label="Username">
              <input
                autoComplete="username"
                data-testid="login-username"
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Il tuo username"
                value={username}
              />
            </AuthField>
            <AuthField icon={<LockKeyhole aria-hidden="true" size={18} />} label="Password">
              <input
                autoComplete="current-password"
                data-testid="login-password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="La tua password"
                type={passwordVisible ? "text" : "password"}
                value={password}
              />
              <PasswordToggle
                visible={passwordVisible}
                onToggle={() => setPasswordVisible((visible) => !visible)}
              />
            </AuthField>

            <Feedback feedback={feedback} />

            <button className="scarlet-auth__primary" data-testid="login-submit" type="submit">
              <span>Entra nel tuo spazio</span>
              <span aria-hidden="true">→</span>
            </button>

            <p className="scarlet-auth__test-hint">
              Accesso di prova <code>scarlet</code> / <code>scarlet</code>
            </p>
          </form>
        ) : (
          <form
            aria-labelledby="register-tab"
            className="scarlet-auth__form"
            id="register-panel"
            onSubmit={submitRegistration}
            role="tabpanel"
          >
            <AuthField icon={<UserRound aria-hidden="true" size={18} />} label="Come ti chiami">
              <input
                autoComplete="name"
                data-testid="register-display-name"
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Nome visualizzato"
                value={displayName}
              />
            </AuthField>
            <AuthField icon={<UserRound aria-hidden="true" size={18} />} label="Username">
              <input
                autoComplete="username"
                data-testid="register-username"
                onChange={(event) => setRegisterUsername(event.target.value)}
                placeholder="Scegli uno username"
                value={registerUsername}
              />
            </AuthField>
            <AuthField icon={<LockKeyhole aria-hidden="true" size={18} />} label="Password">
              <input
                autoComplete="new-password"
                data-testid="register-password"
                onChange={(event) => setRegisterPassword(event.target.value)}
                placeholder="Almeno 6 caratteri"
                type={passwordVisible ? "text" : "password"}
                value={registerPassword}
              />
              <PasswordToggle
                visible={passwordVisible}
                onToggle={() => setPasswordVisible((visible) => !visible)}
              />
            </AuthField>
            <AuthField icon={<LockKeyhole aria-hidden="true" size={18} />} label="Conferma password">
              <input
                autoComplete="new-password"
                data-testid="register-confirmation"
                onChange={(event) => setRegisterConfirmation(event.target.value)}
                placeholder="Ripeti la password"
                type={passwordVisible ? "text" : "password"}
                value={registerConfirmation}
              />
            </AuthField>

            <Feedback feedback={feedback} />

            <button className="scarlet-auth__primary" data-testid="register-submit" type="submit">
              <span>Crea profilo locale</span>
              <span aria-hidden="true">→</span>
            </button>
          </form>
        )}

        <footer className="scarlet-auth__footer">
          <span aria-hidden="true" />
          <p>Prototipo locale · nessun dato viene inviato</p>
        </footer>
      </section>
    </main>
  );
}

function AuthField({
  children,
  icon,
  label
}: {
  children: React.ReactNode;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <label className="scarlet-auth__field">
      <span className="scarlet-auth__field-label">{label}</span>
      <span className="scarlet-auth__input">
        {icon}
        {children}
      </span>
    </label>
  );
}

function PasswordToggle({
  visible,
  onToggle
}: {
  visible: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      aria-label={visible ? "Nascondi password" : "Mostra password"}
      className="scarlet-auth__password-toggle"
      onClick={onToggle}
      type="button"
    >
      {visible ? <EyeOff aria-hidden="true" size={18} /> : <Eye aria-hidden="true" size={18} />}
    </button>
  );
}

function Feedback({
  feedback
}: {
  feedback: { kind: "error" | "success"; message: string } | null;
}) {
  if (!feedback) return null;

  return (
    <p
      className={`scarlet-auth__feedback is-${feedback.kind}`}
      role={feedback.kind === "error" ? "alert" : "status"}
    >
      {feedback.message}
    </p>
  );
}
