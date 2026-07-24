# Frontend

Tailwind React dashboard for the local Scarlet / LLM API Mind runtime.

Development target: V1.56.0. Deployed Core baseline: V1.50.1.

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
- connected `/prototype` Product UI using real Core sessions, memories,
  profile, settings, and resumable Stream V2 events, with responsive flows,
  the fuchsia/scarlet/light-blue Scarlet Signal identity, self-hosted variable
  typography, and an inspectable development-evidence view;
- Tailwind CSS 4 through the official Vite plugin, with raw JSON kept in
  technical detail views for the real cockpit.

The Product UI contract, component equivalence notes, visual tokens, states,
and screenshots live in `../docs/product-ui-prototype.md`. Its local
`scarlet/scarlet` login is only a prototype access gate; it is not backend
authentication.

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

Connected Product UI:

```txt
http://127.0.0.1:5173/prototype
```

## Build

```bash
npm run build
```

Protected HoneyLabs web build:

```bash
npm run build:vps
```

Android debug APK:

```bash
npm run android:debug
```

The Android build requires Android Studio/SDK and JDK 21. The build runner
discovers common JDK 21 installations on macOS and Windows. The resulting APK
is `android/app/build/outputs/apk/debug/app-debug.apk`.

The Android application bundles the Product UI and calls
`https://honeylabs.cloud/scarlet-api`. The owner-approved
`scarlet/scarlet` pair is an intentionally visible test credential compiled
into the debug preview. The native app forwards it only after entry and
forgets the resulting authorization value after a cold start. It is not a
secret or a production account boundary.
