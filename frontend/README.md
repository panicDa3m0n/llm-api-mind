# Frontend

Minimal React debug cockpit for the LLM API Mind baseline runtime.

Current scope:

- persistent chat session creation;
- chat turn submission;
- message list;
- trace panel for `llm.request` and `llm.response`;
- usage counters from turn/trace payloads.

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
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
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
