# Children's Story Generator

An AI-powered pipeline for generating illustrated children's picture books from simple prompts. Built with DSPy for story generation and Google's Nano Banana Pro (Gemini 3 Pro Image) for illustrations.

## Features

- **Story Generation**: Creates complete 12-16 page children's stories from learning goals or themes
- **Character Consistency**: Generates multi-view character model sheets (turnarounds + expressions) for visual consistency
- **Illustration Styles**: LLM-selected art styles based on story tone (watercolor, digital cartoon, pastel, gouache, Ghibli-inspired, claymation)
- **Image QA**: Automatic quality checking with regeneration for text detection, character consistency, and age matching
- **Quality Iteration**: Story text is judged and refined through multiple passes

## Architecture

```
Goal → OutlineGenerator → PageGenerator → QualityJudge
                ↓
        CharacterSheetGenerator (model sheets)
                ↓
        PageIllustrator (with QA loop)
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

# Required: LLM for story generation (one of these)
CEREBRAS_API_KEY=your_cerebras_key  # Recommended: fastest
# OR
OPENROUTER_API_KEY=your_openrouter_key
# OR
OPENAI_API_KEY=your_openai_key
```

## Usage

### Generate an Illustrated Story

```python
from src.programs.story_generator import StoryGenerator
from src.config import configure_dspy

configure_dspy()

generator = StoryGenerator()
story = generator.generate_illustrated(
    goal="teach children about the importance of curiosity",
    debug=True,
)

# Save to directory
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
├── src/
│   ├── signatures/       # DSPy Signatures (input/output contracts)
│   ├── modules/          # DSPy Modules (reusable components)
│   │   ├── outline_generator.py
│   │   ├── page_generator.py
│   │   ├── quality_judge.py
│   │   ├── character_sheet_generator.py
│   │   ├── page_illustrator.py
│   │   ├── illustration_styles.py
│   │   └── image_qa.py
│   ├── programs/         # DSPy Programs (composed pipelines)
│   │   └── story_generator.py
│   └── config.py         # API and model configuration
├── output/               # Generated stories (gitignored)
└── pyproject.toml        # Dependencies
```

## Image QA System

The QA system checks generated illustrations for:

1. **Text Detection**: Ensures no text/words appear in illustrations
2. **Character Consistency**: Compares hair style, face shape, and apparent age against reference sheets
3. **Scene Accuracy**: Validates the illustration matches the prompt

Failed images are automatically regenerated with enhanced prompts (up to 3 attempts).

## License

MIT
