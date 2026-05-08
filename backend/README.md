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

## Test

```bash
pytest
```
