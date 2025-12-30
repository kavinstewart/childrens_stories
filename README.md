# Children's Story Generator

An AI-powered pipeline for generating illustrated children's picture books from simple prompts. Built with DSPy for story generation and Google's Nano Banana Pro (Gemini 3 Pro Image) for illustrations.

## Features

- **Story Generation**: Creates complete 15-16 page children's stories from learning goals or themes
- **Character Consistency**: Generates character reference portraits for visual consistency across illustrations
- **Illustration Styles**: LLM-selected art styles based on story tone (watercolor, digital cartoon, pastel, gouache, Ghibli-inspired, claymation)
- **Image QA**: Automatic quality checking with regeneration for text detection and character consistency
- **Quality Iteration**: Story text is judged and refined through multiple passes
- **REST API**: FastAPI server for async story generation with job management

## Architecture

```
Goal → DirectStoryGenerator (12 spreads in one call) → QualityJudge
                ↓
        CharacterExtractor → BibleGenerator
                ↓
        CharacterSheetGenerator (reference portraits)
                ↓
        SpreadIllustrator (with QA loop)
                ↓
        Illustrated Story
```

## Installation

```bash
# Clone the repository
git clone https://github.com/kavinstewart/childrens_stories.git
cd childrens_stories

# Install dependencies with Poetry
poetry install
```

## Configuration

Create a `.env` file with your API keys:

```bash
# Required: Gemini API for image generation
GOOGLE_API_KEY=your_google_api_key

# Required: LLM for story generation (priority order)
ANTHROPIC_API_KEY=your_anthropic_key  # Recommended: Claude Opus 4.5 (highest quality)
# OR
CEREBRAS_API_KEY=your_cerebras_key    # Fallback: Qwen3-235B (fastest)
# OR
OPENROUTER_API_KEY=your_openrouter_key
# OR
OPENAI_API_KEY=your_openai_key
```

Check your configuration:
```bash
make config
```

## Usage

### Command Line (Recommended)

```bash
# Generate a story with quality iteration (~$0.10-0.30)
make run GOAL="teach about sharing"

# Fast mode - no quality iteration (~$0.05)
make run-fast GOAL="explain photosynthesis to kids"

# Fully illustrated story (~$2-5, requires GOOGLE_API_KEY)
make run-illustrated GOAL="the importance of kindness"
```

Or use the Python script directly:
```bash
python scripts/generate_story.py "teach about sharing" --verbose
python scripts/generate_story.py "kindness" --fast --stdout
```

### REST API

Start the API server:
```bash
make api
# or: python scripts/run_api.py
```

The API runs at `http://localhost:8000` with auto-generated docs at `/docs`.

```bash
# Create a story job
curl -X POST http://localhost:8000/stories \
  -H "Content-Type: application/json" \
  -d '{"goal": "teach about sharing"}'

# Poll for status
curl http://localhost:8000/stories/{story_id}

# Get page illustration
curl http://localhost:8000/stories/{story_id}/pages/1/image --output page1.png
```

### Python API

```python
from backend.config import configure_dspy
from backend.core.programs.story_generator import StoryGenerator

configure_dspy()

generator = StoryGenerator()

# Text-only story
story = generator.forward(goal="teach about sharing")

# Illustrated story
story = generator.generate_illustrated(
    goal="teach children about the importance of curiosity",
    debug=True,
)
story.save_illustrated("output/my_story")
```

### Available Illustration Styles

The LLM automatically selects the best style based on story content:

| Style | Best For |
|-------|----------|
| `watercolor_ink` | Nature, animals, gentle emotions, outdoor adventures |
| `digital_cartoon` | Humor, action, modern settings, friendship |
| `pastel_soft` | Bedtime stories, dreams, magic, comfort |
| `gouache_storybook` | Traditional tales, animals, forests, folklore |
| `ghibli_inspired` | Wonder, discovery, adventure, fantasy, growth |
| `claymation` | Quirky humor, inventions, creativity |

## Project Structure

```
childrens_stories/
├── backend/
│   ├── api/              # FastAPI REST server
│   │   ├── routes/       # API endpoints
│   │   ├── models/       # Request/response schemas
│   │   ├── services/     # Business logic & job management
│   │   └── database/     # PostgreSQL persistence
│   ├── config/           # Configuration modules
│   │   ├── llm.py        # LLM setup (Claude, Cerebras, etc.)
│   │   ├── image.py      # Image generation config
│   │   └── story.py      # Story constants
│   ├── core/
│   │   ├── signatures/   # DSPy Signatures (input/output contracts)
│   │   ├── modules/      # DSPy Modules (reusable components)
│   │   │   ├── direct_story_generator.py
│   │   │   ├── character_extractor.py
│   │   │   ├── bible_generator.py
│   │   │   ├── quality_judge.py
│   │   │   ├── vlm_judge.py
│   │   │   ├── character_sheet_generator.py
│   │   │   ├── spread_illustrator.py
│   │   │   └── image_qa.py
│   │   ├── programs/     # DSPy Programs (composed pipelines)
│   │   │   └── story_generator.py
│   │   └── types.py      # Domain types (Story, Spread, Character, etc.)
│   ├── metrics/          # Evaluation metrics for GEPA optimization
│   └── worker.py         # ARQ background worker
├── cli/                  # CLI entry points
│   ├── generate_story.py
│   └── run_worker.py
├── frontend/             # React Native app (Expo)
├── tests/                # Unit & integration tests
├── data/                 # Runtime data (database, stories)
├── output/               # Generated stories (gitignored)
└── pyproject.toml        # Dependencies (Poetry)
```

## Image QA System

The QA system checks generated illustrations for:

1. **Text Detection**: Ensures no text/words appear in illustrations
2. **Character Consistency**: Compares hair style, face shape, and apparent age against reference portraits
3. **Scene Accuracy**: Validates the illustration matches the prompt

Failed images are automatically regenerated with enhanced prompts (up to 3 attempts).

## Development

```bash
# Run tests
make test

# Show all available commands
make help
```

## License

MIT
