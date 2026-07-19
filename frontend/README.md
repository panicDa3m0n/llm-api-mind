# Frontend

Tailwind React dashboard for the local Scarlet / LLM API Mind runtime.

Development target: V1.52.0. Deployed Core baseline: V1.50.1.

Current scope:

- persistent chat session creation, history, and reload;
- central chat surface with streamed Scarlet turns;
- live Agent Stream panel for runtime events, notes, thinking, tool calls,
  tool results, memory retrieval, and final answers;
- semantic memory panel through `/api/dashboard/memories`;
- operational user profile panel through `/api/dashboard/profile`;
- runtime settings panel through `/api/dashboard/settings`, including active
  profile id, privacy scope, configured country/locale, timezone, and platform
  language;
- developer model inspector for the exact system/runtime/provider/tool request;
- separate `/mobile` consumer surface for chat, memory, profile, and settings;
- isolated `/prototype` static V2 Product UI approval surface with no backend
  calls, schema-realistic fixtures, responsive flows, deterministic preview
  states, and an integrated developer lens;
- Tailwind CSS 4 through the official Vite plugin, with raw JSON kept in
  technical detail views for the real cockpit.

The prototype contract, component equivalence notes, visual tokens, states,
and screenshots live in `../docs/product-ui-prototype.md`. The prototype is
not a real client and must not be connected to Core data before owner approval.

## Setup

From the project root:

```bash
cd frontend
npm install
```

## Run

Start the backend first:

```bash
cd ../backend
.venv/bin/uvicorn app.asgi:app --host 127.0.0.1 --port 8000
```

Then start the frontend:

```bash
cd ../frontend
npm run dev -- --port 5173
```

Open:

```txt
http://127.0.0.1:5173
```

Static Product UI prototype:

```txt
http://127.0.0.1:5173/prototype
```

## Build

```bash
npm run build
```
