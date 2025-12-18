# Children's Story Generator - Claude Guide

## Project Overview
An AI agent that generates high-quality children's picture books from brief goals/themes (e.g., "teach about feedback as a gift" or "explain arteriosclerosis to kids"). Built with DSPy and optimized using GEPA (Reflective Prompt Evolution).

## Core Architecture
- **DSPy Framework**: Modular signatures and programs for story generation
- **GEPA Optimization**: Reflective prompt evolution on each pipeline component
- **Multi-stage Pipeline**: Outline → Pages → Quality Judge → Iterate

## Project Structure
```
childrens_stories/
├── backend/                  # Python backend
│   ├── api/                  # FastAPI HTTP layer
│   │   ├── routes/
│   │   ├── models/
│   │   ├── services/
│   │   └── database/
│   ├── core/                 # Domain logic (DSPy)
│   │   ├── signatures/       # DSPy Signatures (inputs/outputs)
│   │   ├── modules/          # DSPy Modules (reusable components)
│   │   ├── programs/         # DSPy Programs (composed pipelines)
│   │   └── types.py          # Domain types
│   ├── config/               # LLM and image configuration
│   ├── metrics/              # Evaluation metrics with feedback for GEPA
│   └── optimization/         # GEPA optimization scripts
├── frontend/                 # React Native app (Expo) - iPad + web
│   ├── app/                  # Expo Router screens
│   ├── components/           # UI components
│   ├── features/             # Feature modules (data layer)
│   └── lib/                  # Utilities
├── cli/                      # CLI entry points
│   ├── generate_story.py
│   ├── run_api.py
│   └── debug_page.py
├── tests/                    # All tests
│   ├── unit/                 # Fast unit tests
│   └── integration/          # Slow LLM integration tests
├── data/                     # Runtime data (database, stories)
├── docs/                     # Documentation
│   └── prototypes/           # UI prototypes (JSX mockups)
└── output/                   # Generated story outputs
```

## Environment & API Keys
- **IMPORTANT**: API keys are stored in `.env` file at project root
- **NEVER read `.env` directly** - always use `load_dotenv()` from `python-dotenv`
- **Primary**: `CEREBRAS_API_KEY` - Uses Qwen3-235B Instruct via Cerebras (fastest, ~1400 tok/s)
- **Fallbacks**: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`

```python
# Correct way to load API keys
from dotenv import load_dotenv
load_dotenv()
# Keys are now available via os.getenv("CEREBRAS_API_KEY"), etc.
```

## LLM Configuration
- **Model**: `qwen-3-235b-a22b-instruct-2507` (pure instruct, no thinking mode)
- **Provider**: Cerebras Inference (https://inference-docs.cerebras.ai/)
- **Why Cerebras**: 11x faster than GPU clouds, no thinking mode parsing issues
- **Note**: If using OpenRouter with Qwen3 thinking models, add `/no_think` to signature docstrings

## Children's Book Standards
- **Page count**: 32 pages (industry standard)
- **Word count**: 400-600 words total (500 is sweet spot)
- **Structure**: Three-act (25% beginning, 50% middle, 25% end)
- **Per-page words**: ~25-50 words per page

## DSPy & GEPA Patterns

### Dual-LM Architecture
- **Inference LM**: Qwen3-235B Instruct via Cerebras (fast, high-quality creative writing)
- **Reflection LM**: Strong model for GEPA analysis (gpt-4.1, claude-opus)

### Metric Functions for GEPA
GEPA requires metrics that return both score AND textual feedback:
```python
def metric_with_feedback(example, prediction, trace=None, pred_name=None, pred_trace=None):
    score = calculate_score(example, prediction)
    feedback = generate_feedback(example, prediction)
    return dspy.Prediction(score=score, feedback=feedback)
```

### Optimization Pattern
```python
optimizer = dspy.GEPA(
    metric=metric_with_feedback,
    auto="medium",
    reflection_lm=reflection_lm,
    track_stats=True
)
optimized = optimizer.compile(program, trainset=train, valset=val)
```

## Absolute Planning Rules
- **Use `bd` for every task, plan, and follow-up.** No ad-hoc TODO lists, side documents, or checklists.
- Do NOT use the TodoWrite tool - use `bd` instead for all task tracking.
- Keep issue titles concise; put detail in descriptions and comments.
- Break work into dependency-linked issues so `bd ready` always reflects the next unblocked step.

## Essential `bd` Commands
- Create work: `bd create --title="..." --type=task|bug|feature` (add `-d "description"` for context)
- Show work: `bd list --status open`, `bd show <id>`, `bd ready`
- Maintain state: `bd update <id> --status in_progress|open|blocked`, `bd close <id> --reason "..."`
- Model dependencies: `bd dep add <parent> <child>`, inspect with `bd dep tree <id>`

## Development Workflow
1. **Implement baseline** - Get end-to-end pipeline working without optimization
2. **Create training data** - Goals + reference stories for optimization
3. **Build metrics** - Feedback-rich metrics for each component
4. **Run GEPA** - Optimize each component separately
5. **Compose & test** - Integrate optimized modules

## Key Files to Know
- `backend/core/signatures/` - Define input/output contracts
- `backend/core/types.py` - Domain types (Story, Page, etc.)
- `backend/metrics/` - Quality metrics with feedback for GEPA
- `backend/api/` - FastAPI routes and services
- `cli/` - Command-line entry points
- `.env` - API keys (never read directly!)

## Prohibited Behaviors
- Do not read `.env` file directly - use `load_dotenv()`
- Do not hardcode API keys anywhere
- Do not skip GEPA optimization setup (structure code for it from the start)
- Do not create stories over 1000 words (industry standard limit)
- Do not use TodoWrite or maintain parallel planning docs, spreadsheets, or checklists - use `bd` exclusively
- Do not proceed on assumptions when a high-signal question can resolve uncertainty
