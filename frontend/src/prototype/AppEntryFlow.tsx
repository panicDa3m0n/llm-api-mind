import { Capacitor } from "@capacitor/core";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  clearNativeApiBasicAuth,
  fetchHealth,
  setNativeApiBasicAuth
} from "../api";
import { publicAssetPath } from "../runtimeAssets";
import { AuthScreen, type AuthCredentials, type AuthTab } from "./AuthScreen";
import { HomeDashboard, type ProductView } from "./HomeDashboard";
import { SplashScreen } from "./SplashScreen";
import {
  UnavailableFeatureModal,
  type UnavailableFeature
} from "./UnavailableFeatureModal";

type EntryScreen = "splash" | "auth" | "product";
type SplashPhase = "loading" | "greeting" | "leaving";

const DEFAULT_CREDENTIALS: AuthCredentials = {
  username: "scarlet",
  password: "scarlet"
};
const LOCAL_SESSION_KEY = "scarlet-prototype-session-v1";
const LOCAL_PRIVATE_EVIDENCE_KEY = "scarlet-private-evidence-v1";

type LocalSession = {
  authenticated: true;
  username: string;
  view: ProductView;
};

function isProductView(value: unknown): value is ProductView {
  return (
    value === "home" ||
    value === "chat" ||
    value === "memory" ||
    value === "sessions" ||
    value === "profile" ||
    value === "device"
  );
}

function readLocalSession(): LocalSession | null {
  try {
    const value = window.localStorage.getItem(LOCAL_SESSION_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as Partial<LocalSession>;

    if (
      parsed.authenticated !== true ||
      !parsed.username ||
      !isProductView(parsed.view)
    ) {
      window.localStorage.removeItem(LOCAL_SESSION_KEY);
      return null;
    }

    return parsed as LocalSession;
  } catch {
    return null;
  }
}

function writeLocalSession(username: string, view: ProductView) {
  try {
    window.localStorage.setItem(
      LOCAL_SESSION_KEY,
      JSON.stringify({
        authenticated: true,
        username,
        view
      } satisfies LocalSession)
    );
  } catch {
    // The prototype remains usable when private browsing blocks local storage.
  }
}

function readPrivateEvidencePreference(): boolean {
  try {
    return (
      window.localStorage.getItem(LOCAL_PRIVATE_EVIDENCE_KEY) !== "disabled"
    );
  } catch {
    return true;
  }
}

export function AppEntryFlow() {
  const nativePlatform = Capacitor.isNativePlatform();
  const requestedScreen = useMemo(
    () => new URLSearchParams(window.location.search).get("screen"),
    []
  );
  const storedSession = useMemo(
    () => (nativePlatform ? null : readLocalSession()),
    [nativePlatform]
  );
  const initialAuthTab: AuthTab =
    requestedScreen === "register" ? "register" : "login";
  const requestedProductView: ProductView = isProductView(requestedScreen)
    ? requestedScreen
    : "home";
  const isProductReview = isProductView(requestedScreen);
  const initialProductView = isProductReview
    ? requestedProductView
    : storedSession?.view ?? "home";
  const [screen, setScreen] = useState<EntryScreen>(() =>
    isProductReview
      ? "product"
      : requestedScreen === "login" || requestedScreen === "register"
        ? "auth"
        : storedSession
          ? "product"
          : "splash"
  );
  const [splashPhase, setSplashPhase] = useState<SplashPhase>("loading");
  const [appReady, setAppReady] = useState(false);
  const [greetingReady, setGreetingReady] = useState(false);
  const [greetingUnavailable, setGreetingUnavailable] = useState(false);
  const [credentials] = useState<AuthCredentials>(DEFAULT_CREDENTIALS);
  const [unavailable, setUnavailable] =
    useState<UnavailableFeature | null>(null);
  const [authenticatedUser, setAuthenticatedUser] = useState(
    isProductReview ? "scarlet" : storedSession?.username ?? ""
  );
  const [sessionActive, setSessionActive] = useState(Boolean(storedSession));
  const [privateEvidenceUnlocked, setPrivateEvidenceUnlocked] = useState(
    readPrivateEvidencePreference
  );
  const authTransitionTimer = useRef<number | null>(null);

  const enterAuthentication = useCallback(() => {
    if (authTransitionTimer.current !== null) return;

    setSplashPhase("leaving");
    authTransitionTimer.current = window.setTimeout(() => {
      setScreen("auth");
      authTransitionTimer.current = null;
    }, 160);
  }, []);
  const handleGreetingReady = useCallback(() => setGreetingReady(true), []);
  const handleGreetingUnavailable = useCallback(
    () => setGreetingUnavailable(true),
    []
  );

  useEffect(
    () => () => {
      if (authTransitionTimer.current !== null) {
        window.clearTimeout(authTransitionTimer.current);
      }
    },
    []
  );

  useEffect(() => {
    if (screen !== "splash") return;

    let cancelled = false;
    const portrait = new Image();
    portrait.src = publicAssetPath("prototype/scarlet-character-v1.png");
    const portraitReady =
      typeof portrait.decode === "function"
        ? portrait.decode().catch(() => undefined)
        : new Promise<void>((resolve) => {
            portrait.addEventListener("load", () => resolve(), { once: true });
            portrait.addEventListener("error", () => resolve(), { once: true });
          });
    const fontsReady = document.fonts?.ready ?? Promise.resolve();

    void Promise.all([portraitReady, fontsReady])
      .then(
        () =>
          new Promise<void>((resolve) => {
            window.requestAnimationFrame(() =>
              window.requestAnimationFrame(() => resolve())
            );
          })
      )
      .then(() => {
        if (!cancelled) setAppReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, [screen]);

  useEffect(() => {
    if (screen !== "splash" || !appReady || splashPhase !== "loading") {
      return;
    }

    if (requestedScreen === "splash") return;

    if (greetingUnavailable) {
      enterAuthentication();
      return;
    }

    if (greetingReady) {
      setSplashPhase("greeting");
      return;
    }

    const readinessFallback = window.setTimeout(
      () => setGreetingUnavailable(true),
      6000
    );
    return () => window.clearTimeout(readinessFallback);
  }, [
    appReady,
    enterAuthentication,
    greetingReady,
    greetingUnavailable,
    requestedScreen,
    screen,
    splashPhase
  ]);

  const splashProgress =
    appReady && (greetingReady || greetingUnavailable)
      ? 100
      : appReady
        ? 76
        : greetingReady
          ? 68
          : 24;
  const splashStatus =
    appReady && (greetingReady || greetingUnavailable)
      ? requestedScreen === "splash"
        ? "Tutto pronto · modalità revisione"
        : "Tutto pronto"
      : appReady
        ? "Preparo il saluto"
        : greetingReady
          ? "Completo l'interfaccia"
          : "Carico il tuo spazio";

  if (screen === "splash") {
    return (
      <SplashScreen
        onGreetingEnded={enterAuthentication}
        onGreetingReady={handleGreetingReady}
        onGreetingUnavailable={handleGreetingUnavailable}
        phase={splashPhase}
        progress={splashProgress}
        reviewMode={requestedScreen === "splash"}
        status={splashStatus}
      />
    );
  }

  if (screen === "product") {
    return (
      <HomeDashboard
        initialView={initialProductView}
        onLogout={() => {
          clearNativeApiBasicAuth();
          window.localStorage.removeItem(LOCAL_SESSION_KEY);
          window.localStorage.removeItem(LOCAL_PRIVATE_EVIDENCE_KEY);
          setSessionActive(false);
          setAuthenticatedUser("");
          setPrivateEvidenceUnlocked(false);
          setScreen("auth");
        }}
        onPrivateEvidenceChange={(unlocked) => {
          setPrivateEvidenceUnlocked(unlocked);
          try {
            if (unlocked) {
              window.localStorage.setItem(
                LOCAL_PRIVATE_EVIDENCE_KEY,
                "enabled"
              );
            } else {
              window.localStorage.setItem(
                LOCAL_PRIVATE_EVIDENCE_KEY,
                "disabled"
              );
            }
          } catch {
            // The preference remains active for this app lifetime.
          }
        }}
        onViewChange={(view) => {
          if (sessionActive && authenticatedUser) {
            writeLocalSession(authenticatedUser, view);
          }
        }}
        privateEvidenceUnlocked={privateEvidenceUnlocked}
        username={authenticatedUser}
      />
    );
  }

  return (
    <>
      <AuthScreen
        credentials={credentials}
        initialTab={initialAuthTab}
        nativeAuthentication={nativePlatform}
        onLogin={async (username, password) => {
          if (nativePlatform) {
            setNativeApiBasicAuth(username, password);
            try {
              await fetchHealth();
            } catch {
              clearNativeApiBasicAuth();
              throw new Error(
                "Credenziali non riconosciute o connessione a Scarlet non disponibile."
              );
            }
          }
          setAuthenticatedUser(username);
          setSessionActive(true);
          writeLocalSession(username, "home");
          setScreen("product");
        }}
        onRegistrationUnavailable={() =>
          setUnavailable({
            label: "Registrazione",
            detail:
              "Il Core non espone ancora account o registrazione. Questa funzione arriverà in una versione futura."
          })
        }
      />
      <UnavailableFeatureModal
        feature={unavailable}
        onClose={() => setUnavailable(null)}
      />
    </>
  );
}
