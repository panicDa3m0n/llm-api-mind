import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { MobileApp } from "./MobileApp";
import "./styles.css";

const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
const forceMobile = import.meta.env.VITE_FORCE_MOBILE === "true";
const path = window.location.pathname;
const isMobileRoute =
  forceMobile ||
  path.startsWith("/mobile") ||
  Boolean(basePath && path.startsWith(`${basePath}/mobile`));
const RootApp = isMobileRoute ? MobileApp : App;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>
);
