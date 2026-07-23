import assert from "node:assert/strict";
import { existsSync, mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright-core";

const baseUrl = (process.env.PRODUCT_UI_BASE_URL || "http://127.0.0.1:5173")
  .replace(/\/$/, "");
const liveChat = process.env.PRODUCT_UI_LIVE_CHAT === "1";
const replayFailedSessionId =
  process.env.PRODUCT_UI_REPLAY_FAILED_SESSION_ID || "";
const replayFlowSessionId =
  process.env.PRODUCT_UI_REPLAY_FLOW_SESSION_ID || "";
const executablePath =
  process.env.BROWSER_EXECUTABLE ||
  [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe"
  ].find(existsSync);

assert(executablePath, "Chrome o Edge non trovato.");

const browser = await chromium.launch({
  executablePath,
  headless: true
});
const outputDir = path.join(os.tmpdir(), "scarlet-product-ui-smoke");
mkdirSync(outputDir, { recursive: true });
const findings = [];

try {
  findings.push(await runSplash());
  findings.push(await runDesktop());
  findings.push(await runMobile());
  const failures = findings.flatMap((finding) => finding.failures);
  assert.equal(
    failures.length,
    0,
    `Errori browser/rete rilevati:\n${failures.join("\n")}`
  );
  console.log(JSON.stringify({ baseUrl, liveChat, findings, ok: true }, null, 2));
} finally {
  await browser.close();
}

async function runSplash() {
  const context = await browser.newContext({
    locale: "it-IT",
    viewport: { width: 390, height: 844 }
  });
  await context.addInitScript(() => window.localStorage.clear());
  const page = await context.newPage();
  const monitor = monitorFailures(page);
  const startedAt = Date.now();

  try {
    await page.goto(`${baseUrl}/prototype`, {
      waitUntil: "domcontentloaded"
    });
    await page.locator(".scarlet-splash").waitFor({ state: "visible" });
    await page
      .getByTestId("login-submit")
      .waitFor({ state: "visible", timeout: 12_000 });
    const elapsedMs = Date.now() - startedAt;
    assert(
      elapsedMs < 12_000,
      `Splash non ha raggiunto Login entro il limite: ${elapsedMs}ms.`
    );
    await assertNoHorizontalOverflow(page);
    return {
      failures: monitor.failures(),
      name: "splash",
      steps: [`splash-to-login:${elapsedMs}ms`]
    };
  } finally {
    await context.close();
  }
}

async function runDesktop() {
  const context = await browser.newContext({
    locale: "it-IT",
    viewport: { width: 1440, height: 1000 }
  });
  const page = await context.newPage();
  const monitor = monitorFailures(page);
  const steps = [];

  try {
    await page.goto(`${baseUrl}/prototype?screen=login`, {
      waitUntil: "networkidle"
    });
    await page.evaluate(() => window.localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });

    await page.getByTestId("login-username").fill("utente-errato");
    await page.getByTestId("login-password").fill("password-errata");
    await page.getByTestId("login-submit").click();
    await expectVisibleText(page, "Credenziali non riconosciute");
    steps.push("invalid-login");

    await page.getByRole("tab", { name: "Registrazione" }).click();
    await page.getByTestId("register-submit").click();
    await assertCenteredModal(page, { width: 1440, height: 1000 });
    await page.getByRole("button", { name: "Ho capito" }).click();
    steps.push("registration-unavailable");

    await page.getByRole("tab", { name: "Login" }).click();
    await page.getByTestId("login-username").fill("scarlet");
    await page.getByTestId("login-password").fill("scarlet");
    await page.getByTestId("login-submit").click();
    await page.getByTestId("home-dashboard").waitFor({ state: "visible" });
    await expectVisibleText(page, "nessuna fixture");
    await assertNoHorizontalOverflow(page);
    await assertPrototypeDocumentScrollContract(page);
    assert.equal(
      await page.locator(".scarlet-core-status").count(),
      0,
      "Il banner Core/provider non deve occupare le schermate consumer."
    );
    const activeModel = await page.evaluate(async () => {
      const response = await fetch("/health");
      const health = await response.json();
      return health.model;
    });
    assert.equal(
      activeModel,
      "MiniMax-M3",
      "Il runtime locale non usa il modello M3 atteso."
    );
    steps.push("login-home-hydration");

    await page.goto(`${baseUrl}/prototype`, { waitUntil: "networkidle" });
    await page.getByTestId("home-dashboard").waitFor({ state: "visible" });
    assert.equal(
      await page.getByTestId("product-app").getAttribute("data-view"),
      "home",
      "La sessione locale non riprende Home."
    );
    await page.reload({ waitUntil: "networkidle" });
    await page.getByTestId("home-dashboard").waitFor({ state: "visible" });
    steps.push("session-persistence");

    const createResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/chat/sessions") &&
        response.request().method() === "POST"
    );
    await page.getByTestId("new-session").click();
    assert.equal((await createResponse).status(), 200);
    await page.getByTestId("chat-screen").waitFor({ state: "visible" });
    await assertChatChrome(page, { width: 1440, height: 1000 });
    steps.push("real-session-create");

    if (liveChat) {
      const answerCount = await page
        .locator('[data-flow-kind="answer"]')
        .count();
      await page.evaluate(() => {
        window.__scarletFlowEventsSeen = [];
        const capture = () => {
          for (const element of document.querySelectorAll(
            "[data-event-type]"
          )) {
            const eventType = element.getAttribute("data-event-type");
            const status = element.getAttribute("data-flow-status") || "";
            const receipt = `${eventType}:${status}`;
            if (
              eventType &&
              !window.__scarletFlowEventsSeen.includes(receipt)
            ) {
              window.__scarletFlowEventsSeen.push(receipt);
            }
          }
        };
        capture();
        const observer = new MutationObserver(capture);
        observer.observe(document.body, {
          attributes: true,
          childList: true,
          subtree: true
        });
        window.__scarletFlowObserver = observer;
      });
      await page
        .getByLabel("Scrivi a Scarlet")
        .fill("Ciao Scarlet.");
      const streamResponse = page.waitForResponse(
        (response) =>
          response.url().includes("/turn/stream-v2") &&
          response.request().method() === "POST",
        { timeout: 120_000 }
      );
      await page.getByRole("button", { name: "Invia messaggio" }).click();
      assert.equal((await streamResponse).status(), 200);
      await page
        .locator(
          '[data-flow-kind="reflection"][data-flow-status="live"]'
        )
        .waitFor({ state: "visible", timeout: 15_000 });
      await page.waitForFunction(
        (previousCount) => {
          const answerArrived =
            document.querySelectorAll('[data-flow-kind="answer"]').length >
            previousCount;
          const turnFailed = document.querySelector(
            '[data-event-type="turn.failed"]'
          );
          return answerArrived || Boolean(turnFailed);
        },
        answerCount,
        { timeout: 120_000 }
      );
      const canonicalFailure = page.locator(
        '[data-event-type="turn.failed"]'
      );
      if ((await canonicalFailure.count()) > 0) {
        throw new Error(
          `Il turno UI è terminato in errore: ${await canonicalFailure.innerText()}`
        );
      }
      assert(
        (await page.locator('[data-flow-kind="answer"]').count()) >
          answerCount,
        "Lo stream non ha prodotto una nuova risposta."
      );
      const flowEventsSeen = await page.evaluate(() => {
        window.__scarletFlowObserver?.disconnect();
        return window.__scarletFlowEventsSeen || [];
      });
      assert(
        flowEventsSeen.some((receipt) =>
          receipt.startsWith("llm.thinking.started:live")
        ),
        `Lo stato reale di pensiero non si è attivato: ${flowEventsSeen.join(", ")}`
      );
      for (const eventType of [
        "memory.context.built",
        "runtime.context.built",
        "llm.thinking.started"
      ]) {
        assert.equal(
          await page.locator(`[data-event-type="${eventType}"]`).count(),
          1,
          `La proiezione consumer di ${eventType} manca o è duplicata.`
        );
      }
      assert.equal(
        await page.locator('[data-event-type="llm.thinking.captured"]').count(),
        0,
        "Il contenuto thinking privato non deve entrare nel flusso consumer."
      );
      await page
        .getByRole("button", { name: "Invia messaggio" })
        .waitFor({ state: "visible" });
      assert.equal(
        await page.getByRole("button", { name: "Invia messaggio" }).isEnabled(),
        false,
        "Il composer deve tornare inattivo dopo aver svuotato il draft."
      );
      steps.push(`real-v2-turn:${flowEventsSeen.join("|")}`);
    }

    await clickDock(page, "Sessioni");
    await page.getByTestId("sessions-screen").waitFor({ state: "visible" });
    assert(
      (await page.locator(".scarlet-sessions-screen__list article").count()) >
        0,
      "La sessione appena creata non compare nella UI."
    );
    steps.push("sessions-list");

    if (replayFlowSessionId) {
      await page
        .getByPlaceholder("Cerca titolo o ID sessione")
        .fill(replayFlowSessionId);
      const replaySession = page
        .locator(".scarlet-sessions-screen__list article")
        .filter({ hasText: replayFlowSessionId });
      assert.equal(
        await replaySession.count(),
        1,
        "Sessione completa di regressione non trovata."
      );
      await replaySession.getByRole("button").click();
      await page.getByTestId("chat-screen").waitFor({ state: "visible" });
      for (const eventType of [
        "memory.context.built",
        "runtime.context.built",
        "llm.thinking.started"
      ]) {
        const activity = page.locator(`[data-event-type="${eventType}"]`);
        await activity.waitFor({ state: "visible" });
        assert.equal(
          await activity.getAttribute("data-flow-status"),
          "completed",
          `Il replay di ${eventType} deve essere completato.`
        );
      }
      await page.locator('[data-event-type="runtime.context.built"]').click();
      await assertCenteredEventModal(page, { width: 1440, height: 1000 });
      await page
        .getByTestId("chat-event-detail-modal")
        .getByText("Blocchi runtime", { exact: true })
        .waitFor({ state: "visible" });
      await page.screenshot({
        fullPage: false,
        path: path.join(outputDir, "desktop-chat-event-modal.png")
      });
      await page
        .getByRole("button", { name: "Chiudi dettagli evento" })
        .click();
      await page.locator('[data-event-type="memory.context.built"]').click();
      await assertCenteredEventModal(page, { width: 1440, height: 1000 });
      await page
        .getByTestId("chat-event-detail-modal")
        .getByText("Ricordi selezionati", { exact: true })
        .waitFor({ state: "visible" });
      await page
        .getByRole("button", { name: "Chiudi dettagli evento" })
        .click();
      assert.equal(
        await page.locator('[data-event-type="llm.thinking.captured"]').count(),
        0,
        "Il replay non deve mostrare il thinking privato."
      );
      await page.screenshot({
        fullPage: false,
        path: path.join(outputDir, "desktop-chat-replay.png")
      });
      steps.push("completed-turn-activity-replay");
      await clickDock(page, "Sessioni");
      await page.getByTestId("sessions-screen").waitFor({ state: "visible" });
    }

    if (replayFailedSessionId) {
      await page
        .getByPlaceholder("Cerca titolo o ID sessione")
        .fill(replayFailedSessionId);
      const failedSession = page
        .locator(".scarlet-sessions-screen__list article")
        .filter({ hasText: replayFailedSessionId });
      assert.equal(
        await failedSession.count(),
        1,
        "Sessione fallita di regressione non trovata."
      );
      await failedSession.getByRole("button").click();
      await page.getByTestId("chat-screen").waitFor({ state: "visible" });
      await page
        .locator('[data-event-type="turn.failed"]')
        .waitFor({ state: "visible" });
      assert.equal(
        await page.locator('[data-event-type="turn.failed"]').count(),
        1,
        "Il terminale fallito deve produrre una sola bolla canonica."
      );
      assert(
        (await page
          .locator('[data-event-type="turn.failed"]')
          .innerText()).includes("Non sono riuscita a completare"),
        "Il fallimento tecnico non è tradotto in un messaggio consumer."
      );
      assert.equal(
        await page.locator('[data-event-type="ui.transport.error"]').count(),
        0,
        "Un turn.failed canonico non deve essere duplicato come errore di trasporto."
      );
      steps.push("failed-turn-single-bubble");
    }

    await clickDock(page, "Memoria");
    await page.getByTestId("memory-screen").waitFor({ state: "visible" });
    const memorySearch = page.getByPlaceholder("Cerca nei ricordi caricati");
    await memorySearch.fill("nessun-risultato-ui-7bb205");
    await expectVisibleText(page, "Nessun ricordo reale corrisponde");
    await memorySearch.fill("");
    const memoryRows = page.locator(".scarlet-memory-screen__list > button");
    const memoryCount = await memoryRows.count();
    if (memoryCount > 0) {
      await memoryRows.nth(0).click();
      await expectVisibleText(page, "Dettaglio del ricordo");
    }
    steps.push(`memory-search-detail:${memoryCount}`);

    await clickDock(page, "Profilo");
    await page.getByTestId("profile-screen").waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Risposte concise" }).click();
    await assertCenteredModal(page, { width: 1440, height: 1000 });
    await page.getByRole("button", { name: "Chiudi" }).click();
    steps.push("settings-unavailable");

    const saveResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/dashboard/settings") &&
        response.request().method() === "PUT"
    );
    await page
      .getByRole("button", { name: "Salva profilo e ambiente" })
      .click();
    assert.equal((await saveResponse).status(), 200);
    await expectVisibleText(page, "Impostazioni salvate nel Core.");
    steps.push("real-settings-save");

    const privateEvidenceToggle = page.getByRole("button", {
      name: "Evidenze private"
    });
    await privateEvidenceToggle.click();
    assert.equal(
      await privateEvidenceToggle.getAttribute("aria-pressed"),
      "true",
      "Lo switch delle evidenze private non si è attivato."
    );
    await page.reload({ waitUntil: "networkidle" });
    await page.getByTestId("profile-screen").waitFor({ state: "visible" });
    assert.equal(
      await page
        .getByRole("button", { name: "Evidenze private" })
        .getAttribute("aria-pressed"),
      "true",
      "La preferenza locale delle evidenze private non persiste al reload."
    );
    steps.push("private-evidence-setting-persistence");

    if (replayFlowSessionId) {
      await clickDock(page, "Sessioni");
      await page
        .getByPlaceholder("Cerca titolo o ID sessione")
        .fill(replayFlowSessionId);
      const replaySession = page
        .locator(".scarlet-sessions-screen__list article")
        .filter({ hasText: replayFlowSessionId });
      await replaySession.getByRole("button").click();
      await page.getByTestId("chat-screen").waitFor({ state: "visible" });
      const privateThinking = page.locator(
        '[data-event-type="llm.thinking.captured"]'
      );
      await privateThinking.waitFor({ state: "visible" });
      await privateThinking.click();
      await assertCenteredEventModal(page, { width: 1440, height: 1000 });
      const eventModal = page.getByTestId("chat-event-detail-modal");
      await eventModal
        .getByText("contenuto del ragionamento interno protetto", {
          exact: false
        })
        .waitFor({ state: "visible" });
      await eventModal
        .getByText("Evidenza privata sbloccata", { exact: false })
        .waitFor({ state: "visible" });
      await page
        .getByRole("button", { name: "Chiudi dettagli evento" })
        .click();
      steps.push("private-event-redacted-inspection");
      await clickDock(page, "Profilo");
      await page.getByTestId("profile-screen").waitFor({ state: "visible" });
    }

    await page.screenshot({
      fullPage: true,
      path: path.join(outputDir, "desktop-profile.png")
    });

    await page.getByRole("button", { name: "Esci" }).click();
    await page.getByTestId("login-submit").waitFor({ state: "visible" });
    assert.equal(
      await page.evaluate(() =>
        window.localStorage.getItem("scarlet-prototype-session-v1")
      ),
      null,
      "Logout non ha eliminato la sessione locale."
    );
    assert.equal(
      await page.evaluate(() =>
        window.localStorage.getItem("scarlet-private-evidence-v1")
      ),
      null,
      "Logout non ha eliminato la preferenza locale sulle evidenze private."
    );
    steps.push("logout");

    return {
      failures: monitor.failures(),
      name: "desktop",
      steps
    };
  } finally {
    await context.close();
  }
}

async function runMobile() {
  const viewport = { width: 390, height: 844 };
  const context = await browser.newContext({
    deviceScaleFactor: 1,
    hasTouch: true,
    isMobile: true,
    locale: "it-IT",
    viewport
  });
  const page = await context.newPage();
  const monitor = monitorFailures(page);
  const steps = [];

  try {
    await page.goto(`${baseUrl}/prototype?screen=login`, {
      waitUntil: "networkidle"
    });
    await page.evaluate(() => window.localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    await page.getByTestId("login-username").fill("scarlet");
    await page.getByTestId("login-password").fill("scarlet");
    await page.getByTestId("login-submit").click();
    await page.getByTestId("home-dashboard").waitFor({ state: "visible" });
    await expectVisibleText(page, "nessuna fixture");
    await assertNoHorizontalOverflow(page);
    await assertPrototypeDocumentScrollContract(page);

    const homeMetrics = await page.evaluate(() => ({
      bodyClientHeight: document.body.clientHeight,
      bodyRectHeight: document.body.getBoundingClientRect().height,
      bodyScrollHeight: document.body.scrollHeight,
      clientHeight: document.documentElement.clientHeight,
      homeHeight:
        document.querySelector(".scarlet-home")?.getBoundingClientRect().height ??
        0,
      rootHeight:
        document.querySelector("#root")?.getBoundingClientRect().height ?? 0,
      scrollHeight: document.documentElement.scrollHeight
    }));
    assert(
      Math.max(homeMetrics.scrollHeight, homeMetrics.bodyScrollHeight) >
        homeMetrics.clientHeight,
      `Home mobile non espone lo scroll pagina: ${JSON.stringify(homeMetrics)}`
    );
    const scrollPosition = await page.evaluate(() => {
      document.documentElement.scrollTop = 120;
      document.body.scrollTop = 120;
      const position = Math.max(
        document.documentElement.scrollTop,
        document.body.scrollTop
      );
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      return position;
    });
    assert(
      scrollPosition > 0,
      `Home mobile ha contenuto eccedente ma non scorre: ${JSON.stringify(homeMetrics)}`
    );
    steps.push(
      `home-scroll:${Math.max(homeMetrics.scrollHeight, homeMetrics.bodyScrollHeight)}`
    );

    for (const target of ["Memoria", "Sessioni", "Profilo"]) {
      await clickDock(page, target);
      await assertNoHorizontalOverflow(page);
      steps.push(`mobile-${target.toLocaleLowerCase("it")}`);
    }

    await page.getByRole("button", { name: "Esporta dati" }).click();
    await assertCenteredModal(page, viewport);
    await page.getByRole("button", { name: "Ho capito" }).click();
    steps.push("mobile-centered-modal");

    if (replayFlowSessionId) {
      await clickDock(page, "Sessioni");
      await page
        .getByPlaceholder("Cerca titolo o ID sessione")
        .fill(replayFlowSessionId);
      const replaySession = page
        .locator(".scarlet-sessions-screen__list article")
        .filter({ hasText: replayFlowSessionId });
      await replaySession.getByRole("button").click();
      await page.getByTestId("chat-screen").waitFor({ state: "visible" });
      await page.locator('[data-event-type="memory.context.built"]').click();
      await assertCenteredEventModal(page, viewport);
      await page
        .getByRole("button", { name: "Chiudi dettagli evento" })
        .click();
      steps.push("mobile-event-detail-modal");
    }

    await clickDock(page, "Chat");
    await page.getByTestId("chat-screen").waitFor({ state: "visible" });
    await assertChatChrome(page, viewport);
    await assertNoHorizontalOverflow(page);
    steps.push("mobile-chat-layout");

    await page.screenshot({
      fullPage: false,
      path: path.join(outputDir, "mobile-chat.png")
    });

    return {
      failures: monitor.failures(),
      name: "mobile",
      steps
    };
  } finally {
    await context.close();
  }
}

function monitorFailures(page) {
  const errors = [];

  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().includes("favicon.ico")
    ) {
      errors.push(`console: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("requestfailed", (request) => {
    const expectedGreetingCut =
      new URL(request.url()).pathname ===
        "/prototype/avatar/static/motion/scarlet-startup-greeting-happyhorse-v1.mp4" &&
      request.failure()?.errorText === "net::ERR_ABORTED";
    if (expectedGreetingCut) return;
    errors.push(
      `requestfailed: ${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`
    );
  });
  page.on("response", (response) => {
    if (
      response.status() >= 400
    ) {
      errors.push(
        `http ${response.status()}: ${response.request().method()} ${response.url()}`
      );
    }
  });

  return {
    failures: () => [...new Set(errors)]
  };
}

async function clickDock(page, label) {
  const button = page.locator(
    `.scarlet-home__dock button[data-view-target="${dockTarget(label)}"]`
  );
  assert.equal(await button.count(), 1, `Dock ${label} non univoco.`);
  await button.click();
}

function dockTarget(label) {
  return {
    Chat: "chat",
    Home: "home",
    Memoria: "memory",
    Profilo: "profile",
    Sessioni: "sessions"
  }[label];
}

async function expectVisibleText(page, text) {
  const locator = page.getByText(text, { exact: false });
  await locator.waitFor({ state: "visible" });
}

async function assertCenteredModal(page, viewport) {
  const modal = page.getByTestId("unavailable-modal");
  await modal.waitFor({ state: "visible" });
  await expectVisibleText(page, "Funzione non disponibile");
  const dialog = modal.locator(".scarlet-unavailable__dialog");
  const box = await dialog.boundingBox();
  assert(box, "Modale senza dimensioni.");
  assert(
    Math.abs(box.x + box.width / 2 - viewport.width / 2) <= 2,
    "Il modale non è centrato orizzontalmente."
  );
  assert(
    Math.abs(box.y + box.height / 2 - viewport.height / 2) <= 2,
    "Il modale non è centrato verticalmente."
  );
}

async function assertCenteredEventModal(page, viewport) {
  const modal = page.getByTestId("chat-event-detail-modal");
  await modal.waitFor({ state: "visible" });
  const dialog = modal.locator(".scarlet-event-detail__dialog");
  const box = await dialog.boundingBox();
  assert(box, "Modale evento senza dimensioni.");
  assert(
    Math.abs(box.x + box.width / 2 - viewport.width / 2) <= 2,
    "Il modale evento non è centrato orizzontalmente."
  );
  assert(
    Math.abs(box.y + box.height / 2 - viewport.height / 2) <= 2,
    "Il modale evento non è centrato verticalmente."
  );
}

async function assertNoHorizontalOverflow(page) {
  const metrics = await page.evaluate(() => ({
    body: document.body.scrollWidth,
    document: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth
  }));
  assert(
    metrics.body <= metrics.viewport && metrics.document <= metrics.viewport,
    `Overflow orizzontale: ${JSON.stringify(metrics)}`
  );
}

async function assertPrototypeDocumentScrollContract(page) {
  const declarations = await page.evaluate(() => {
    const matches = [];
    const visit = (rules) => {
      for (const rule of rules) {
        if ("cssRules" in rule) {
          visit(rule.cssRules);
        }
        if (
          "selectorText" in rule &&
          (
            (
              rule.selectorText?.includes("html.scarlet-prototype-document") &&
              rule.selectorText?.includes("body.scarlet-prototype-document")
            ) ||
            rule.selectorText?.includes(
              "body.scarlet-prototype-document #root"
            )
          )
        ) {
          matches.push({
            height: rule.style.height,
            minHeight: rule.style.minHeight,
            selector: rule.selectorText
          });
        }
      }
    };
    for (const sheet of document.styleSheets) {
      try {
        visit(sheet.cssRules);
      } catch {
        // Ignore browser-protected third-party sheets.
      }
    }
    return matches;
  });
  assert(declarations.length > 0, "Contratto CSS documento prototipo non trovato.");
  assert(
    declarations.every(
      (declaration) => !declaration.height && !declaration.minHeight
    ),
    `Il documento prototipo non deve fissare height/min-height: ${JSON.stringify(declarations)}`
  );
}

async function assertChatChrome(page, viewport) {
  const metrics = await page.evaluate(() => {
    const header = document.querySelector(".scarlet-chat__header");
    const scroller = document.querySelector('[data-testid="chat-message-scroll"]');
    const composer = document.querySelector('[data-testid="chat-composer"]');
    const dock = document.querySelector(".scarlet-home__dock");
    const rect = (element) => {
      const value = element?.getBoundingClientRect();
      return value
        ? { bottom: value.bottom, height: value.height, top: value.top }
        : null;
    };
    return {
      bodyHeight: document.body.getBoundingClientRect().height,
      composer: rect(composer),
      dock: rect(dock),
      header: rect(header),
      scroller: rect(scroller)
    };
  });

  assert(metrics.header && metrics.scroller && metrics.composer && metrics.dock);
  assert(metrics.header.bottom <= metrics.scroller.top + 1);
  assert(metrics.scroller.bottom <= metrics.composer.top + 1);
  assert(metrics.composer.bottom <= metrics.dock.top + 8);
  assert(metrics.dock.bottom <= viewport.height + 1);
  assert(
    Math.abs(metrics.bodyHeight - viewport.height) <= 1,
    `Chat non occupa una viewport esatta: ${metrics.bodyHeight}/${viewport.height}`
  );
}
