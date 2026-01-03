# Children's Story Generator

AI agent that generates illustrated children's picture books from brief goals/themes. Built with DSPy and FastAPI.

## Tech Stack
- **Backend**: Python, FastAPI, DSPy, Poetry
- **Frontend**: React Native (Expo), TypeScript
- **LLM**: Qwen3-235B via Cerebras (`backend/config/`)
- **Database**: PostgreSQL with asyncpg

## Commands

```bash
# Backend
poetry run pytest tests/unit/ -v          # Unit tests
poetry run pytest tests/integration/ -v   # Integration tests (requires services)
poetry add <package>                      # Add dependency (never pip install)

# Frontend
cd frontend && npx playwright test        # E2E tests (requires APP_PIN in .env)
```

## Project Structure
- `backend/api/` - FastAPI routes, services, database
- `backend/core/` - DSPy modules, programs, types
- `backend/metrics/` - Quality evaluation metrics
- `frontend/app/` - Expo Router screens
- `tests/unit/`, `tests/integration/` - Test suites
- `cli/` - CLI entry points

## Key Conventions
- **API keys**: Use `load_dotenv()`, never read `.env` directly
- **Dependencies**: Use Poetry (`poetry add`), never pip
- **Task tracking**: Use `bd` for all planning (not TodoWrite)
- **Testing**: Run relevant tests before closing implementation work

## Task Tracking with `bd`
```bash
bd create --title="..." --type=task|bug|feature
bd list --status open
bd ready                    # Next unblocked task
bd close <id> --reason "..."
```

## Detailed Documentation
For task-specific guidance, see:
- `docs/agent/dspy-patterns.md` - DSPy/GEPA optimization patterns
- `docs/agent/frontend-development.md` - Frontend dev, ports, E2E tests
- `docs/agent/story-standards.md` - Children's book requirements

## Prohibited
- Reading `.env` directly (use `load_dotenv()`)
- Hardcoding API keys
- Creating stories over 1000 words
- Using TodoWrite (use `bd` instead)
