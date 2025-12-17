# Illustrated Story Example

**Goal**: "teach kids that trying new things can be scary but rewarding"

## Output

- `story.md` - The generated story with embedded image references
- `images/` - 15 page illustrations (PNG)
- `character_refs/` - 3 character reference sheets (PNG)

## Stats

- Pages: 15
- Word count: ~600
- Model: Claude Opus 4.5 (text), Gemini 3 Pro Image (illustrations)
- Character refs: Pepper, Milo, Gran-Gran
- Illustration style: Auto-selected based on story content

## Story Summary

"Pepper and the Backward Dive" - Same story as simple_story example, but with full illustrations.

## Character Reference Sheets

These are generated first to ensure visual consistency across all page illustrations:

- `Pepper_reference.png` - The protagonist, a young penguin
- `Milo_reference.png` - Pepper's supportive friend
- `Gran_Gran_reference.png` - Pepper's wise grandmother

## Page Illustrations

Each page illustration is generated using:
1. The illustration prompt from the story text
2. Character reference images for consistency
3. The selected illustration style
4. Image QA to ensure no text in images

## Reproduction

```bash
make run-illustrated GOAL="teach kids that trying new things can be scary but rewarding"
```

Note: Requires `GOOGLE_API_KEY` in `.env` for image generation.
