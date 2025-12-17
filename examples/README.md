# Examples

Real outputs from the Children's Story Generator pipeline.

## Directory Structure

```
examples/
├── simple_story/       # Text-only story (no illustrations)
│   └── story.md
└── illustrated_story/  # Fully illustrated story
    ├── story.md
    ├── images/         # Page illustrations
    └── character_refs/ # Character reference sheets
```

## simple_story/

A 15-page story generated with quality iteration. Demonstrates:
- Story structure (protagonist goal, stakes, emotional arc)
- Industry-standard format (500-600 words, ~40 words/page)
- Illustration prompts for each page (not yet rendered)

**Goal**: "teach kids that trying new things can be scary but rewarding"
**Result**: "Pepper and the Backward Dive" - A penguin overcomes her fear of diving

**Command used**:
```bash
make run GOAL="teach kids that trying new things can be scary but rewarding"
```

## illustrated_story/

A fully illustrated story with:
- Character reference sheets (for visual consistency)
- Page illustrations generated with Nano Banana Pro (Gemini 3 Pro Image)
- Image QA verification (text-free, character consistency)

**Command used**:
```bash
make run-illustrated GOAL="teach about the importance of friendship"
```

## Generating Your Own

```bash
# Simple story (text only, ~$0.10-0.30)
make run GOAL="your learning goal here"

# Fast story (no quality iteration, ~$0.05)
make run-fast GOAL="your learning goal here"

# Illustrated story (~$2-5, requires GOOGLE_API_KEY)
make run-illustrated GOAL="your learning goal here"
```
