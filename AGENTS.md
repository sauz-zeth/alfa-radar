# Repository Guidelines

## Project Structure & Module Organization

This monorepo contains the Alfa-Future news analytics service:

- `back/` contains the FastAPI backend, SQLAlchemy models, migrations, seed scripts, and tests in `back/tests/`.
- `front/` contains the Bun + React SPA, API clients, screens, styles, and Playwright tests.
- `ml/` contains the offline clustering/ranking pipeline, notebooks, models, and tests.
- `docs/` contains deployment notes; `artifacts/` holds design drafts.

## Build, Test, and Development Commands

From `back/`:

```bash
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn back.main:app --reload
uv run pytest -q
uv run ruff check .
```

From `front/`, use `bun install`, `bun dev`, `bun run build`, or `bun run test:visual`. Start the full stack with `docker compose up --build` at the repository root. See `ml/README.md` for ML commands and inputs.

## Coding Style & Naming Conventions

Python follows each `pyproject.toml`, four-space indentation, type hints, and Ruff's 100-character limit. Ruff enforces `E`, `F`, `I`, `UP`, `B`, and `SIM`. Use `snake_case` for Python modules/functions and `PascalCase` for React components. Keep schemas, services, and routes in their existing layers.

## Testing Guidelines

Backend tests use `pytest`/`pytest-asyncio`; place them in `back/tests/` with `test_*.py` names. Frontend visual coverage uses Playwright via `bun run test:visual`. Add focused tests for new routes, services, parsing, and migrations. Do not commit generated outputs, model caches, or `.env` files.

## Commit & Pull Request Guidelines

Recent commits use short, imperative, lowercase summaries such as `fix search` and `add deploy guide`. Keep commits focused. Pull requests should explain the change, affected components, validation commands, and any migrations or environment variables. Include screenshots or Playwright evidence for frontend changes.

## Security & Configuration

Copy `.env.example` files locally; never commit secrets, JWT keys, or API tokens. Use `LLM_PROVIDER=stub` for offline backend development. Treat downloaded ML models as private data.
