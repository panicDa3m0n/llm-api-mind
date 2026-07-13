# Frontend

Tailwind React dashboard for the local Scarlet / LLM API Mind runtime.

App baseline: V1.29.1.

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
- Tailwind component styling with raw JSON kept in technical detail views.

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

## Build

```bash
npm run build
```
