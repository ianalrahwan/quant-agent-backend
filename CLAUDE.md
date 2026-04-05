# Quant Agent Backend

## Project

LangGraph agent backend for quantitative volatility analysis. Separate repo from the Next.js frontend (quant-agent-service).

## Code Standards

- Python 3.12+, type hints everywhere, Pydantic v2 for all I/O
- UV for dependency management
- Async by default (FastAPI + httpx + asyncio)
- No print statements — use structlog
- Tests: pytest + pytest-asyncio + httpx
- Separate pure computation from LLM interpretation

## Commands

- `uv run pytest` — run tests
- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run uvicorn app.main:app --reload` — dev server
- `docker compose up` — full local stack (postgres, redis, app)

## Workflow

- TDD: write failing test → implement → verify pass → commit
- Run /simplify before committing
