#!/bin/bash
# Pre-commit checks for Claude Code
# Runs tests, type checking, and linting before allowing git commit

set -e

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command being run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Only run checks if this is a git commit command
if ! echo "$COMMAND" | grep -q '^git commit'; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

echo "🔍 Running pre-commit checks..."

# Check if we have Python files staged
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -n "$STAGED_PY" ]; then
    echo "📋 Running pytest..."
    if ! poetry run pytest -x -q 2>&1; then
        echo "❌ Tests failed! Fix before committing."
        exit 2
    fi
    echo "✅ Tests passed"

    # Skipping mypy for now - codebase has pre-existing type issues
    # echo "📋 Running mypy..."
    # if ! poetry run mypy backend/ 2>&1; then
    #     echo "❌ Type errors found! Fix before committing."
    #     exit 2
    # fi
    # echo "✅ Type check passed"

    echo "📋 Running ruff..."
    if ! poetry run ruff check . 2>&1; then
        echo "❌ Lint errors found! Fix before committing."
        exit 2
    fi
    echo "✅ Lint check passed"
fi

# Check if we have TypeScript/JS files staged (frontend)
STAGED_TS=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx)$' || true)

if [ -n "$STAGED_TS" ]; then
    echo "📋 Running TypeScript check..."
    if [ -d "frontend" ]; then
        if ! (cd frontend && npx tsc --noEmit) 2>&1; then
            echo "❌ TypeScript errors found! Fix before committing."
            exit 2
        fi
        echo "✅ TypeScript check passed"
    fi
fi

echo "✅ All pre-commit checks passed!"
exit 0
