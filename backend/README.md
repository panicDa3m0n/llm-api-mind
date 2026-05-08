# Backend

FastAPI backend for the LLM API Mind experimental runtime.

Current scope:

- typed environment configuration;
- `/health` endpoint;
- pytest smoke test;
- ready for the MiniMax provider client in the next slice.

## Setup

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
cp .env.example .env
```

Add your MiniMax key to `backend/.env`:

```txt
MINIMAX_API_KEY=...
```

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

```txt
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## MiniMax Smoke Test

After adding `MINIMAX_API_KEY` to `backend/.env`, run:

```bash
python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import create_app

client = TestClient(create_app())
response = client.post("/api/debug/llm-smoke-test", json={
    "prompt": "Reply with exactly: pong",
    "max_tokens": 128,
})
print(response.status_code)
print(response.json())
PY
```

## Test

```bash
pytest
```
