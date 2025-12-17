# Children's Story Generator - Common Commands
#
# Usage: make <target>
#
# This Makefile serves as executable documentation for common operations.

.PHONY: help run run-fast run-illustrated debug optimize test clean

# Default target - show help
help:
	@echo "Children's Story Generator"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Story Generation:"
	@echo "  run GOAL=\"...\"        Generate a story with quality loop (default)"
	@echo "  run-fast GOAL=\"...\"   Generate a story without quality iteration"
	@echo "  run-illustrated GOAL=\"...\"  Generate a fully illustrated story"
	@echo ""
	@echo "Development:"
	@echo "  debug                Debug page generation"
	@echo "  optimize             Run GEPA optimization on PageWriter"
	@echo "  test                 Run tests (when available)"
	@echo "  clean                Remove generated output files"
	@echo ""
	@echo "Examples:"
	@echo "  make run GOAL=\"teach about sharing\""
	@echo "  make run-fast GOAL=\"explain photosynthesis to kids\""
	@echo "  make run-illustrated GOAL=\"the importance of kindness\""

# Generate a story with quality iteration loop
run:
ifndef GOAL
	@echo "Error: GOAL is required. Usage: make run GOAL=\"your story goal\""
	@exit 1
endif
	poetry run python scripts/generate_story.py "$(GOAL)" --verbose

# Generate a story without quality iteration (faster, cheaper)
run-fast:
ifndef GOAL
	@echo "Error: GOAL is required. Usage: make run-fast GOAL=\"your story goal\""
	@exit 1
endif
	poetry run python scripts/generate_story.py "$(GOAL)" --fast --verbose

# Generate a fully illustrated story
run-illustrated:
ifndef GOAL
	@echo "Error: GOAL is required. Usage: make run-illustrated GOAL=\"your story goal\""
	@exit 1
endif
	poetry run python -c "\
from src.config import configure_dspy; \
from src.programs.story_generator import StoryGenerator; \
configure_dspy(); \
gen = StoryGenerator(); \
story = gen.generate_illustrated('$(GOAL)', debug=True); \
paths = story.save_illustrated('output/illustrated_' + story.title.replace(' ', '_')[:20]); \
print(f'Saved to: {paths[\"output_dir\"]}')"

# Debug page generation
debug:
	poetry run python scripts/debug_page.py

# Run GEPA optimization on PageWriter
optimize:
	poetry run python -m src.optimization.optimize_page_writer

# Run tests (placeholder - tests not yet implemented)
test:
	@echo "Tests not yet implemented. Add tests to tests/ directory."
	@exit 0

# Remove generated output files
clean:
	rm -rf output/*
	@echo "Cleaned output/ directory"

# Install dependencies
install:
	poetry install

# Show current configuration
config:
	@echo "Checking API key configuration..."
	@python -c "from dotenv import load_dotenv; import os; load_dotenv(); \
keys = ['ANTHROPIC_API_KEY', 'CEREBRAS_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY']; \
[print(f'{k}: {\"configured\" if os.getenv(k) else \"not set\"}') for k in keys]"
