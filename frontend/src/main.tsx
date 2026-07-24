import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { MobileApp } from "./MobileApp";
import "./styles.css";

const PrototypeApp = React.lazy(() =>
  import("./prototype/PrototypeApp").then((module) => ({
    default: module.PrototypeApp
  }))
);

const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
const forceMobile = import.meta.env.VITE_FORCE_MOBILE === "true";
const path = window.location.pathname;
const isPrototypeRoute =
  path.startsWith("/prototype") ||
  Boolean(basePath && path.startsWith(`${basePath}/prototype`));
const isMobileRoute =
  forceMobile ||
  path.startsWith("/mobile") ||
  Boolean(basePath && path.startsWith(`${basePath}/mobile`));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isPrototypeRoute ? (
      <React.Suspense fallback={null}>
        <PrototypeApp />
      </React.Suspense>
    ) : isMobileRoute ? (
      <MobileApp />
    ) : (
      <App />
    )}
  </React.StrictMode>
);
