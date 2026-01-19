# Children's Story Generator

AI agent that generates illustrated children's picture books from brief goals/themes. Built with DSPy and FastAPI.

## Tech Stack
- **Backend**: Python, FastAPI, DSPy, Poetry
- **Frontend**: React Native (Expo), TypeScript
- **LLM**: Claude Opus 4.5 via Anthropic API (`backend/config/`)
- **Image Generation**: Gemini 3 Pro Image (Nano Banana Pro) via Google API
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

## Services (systemd)

All services run as **user-level systemd** units (not system-level):

```bash
# List services
systemctl --user list-units --type=service | grep -E "stories|expo"

# Manage services
systemctl --user restart expo-frontend.service
systemctl --user status stories-backend.service
journalctl --user -u expo-frontend.service -f  # Follow logs
```

| Service | Description |
|---------|-------------|
| `expo-frontend.service` | Metro bundler + Expo tunnel (port 8081) |
| `stories-backend.service` | FastAPI backend |
| `stories-worker.service` | ARQ background worker |

Service files: `~/.config/systemd/user/*.service`

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

## Proactive Issue Tracking

When you notice bugs, type errors, or issues while working on other tasks, you MUST:
1. Create a bead for each issue using `bd create --type=bug --title="..."`
2. Call out the issue to the user in your response
3. Do NOT ignore issues just because they're "unrelated" or "pre-existing"

This applies to: TypeScript errors, broken tests, missing dependencies, dead code, security issues, or anything that would break the build or degrade quality.

## Prohibited
- Reading `.env` directly (use `load_dotenv()`)
- Hardcoding API keys
- Creating stories over 1000 words
- Using TodoWrite (use `bd` instead)
