# Children's Book Standards

## Structural Requirements
- **Spread count**: 12 spreads (a spread = two facing pages; fixed structural requirement)
- **Word count**: 400-600 words total (ideal), 300-800 acceptable
- **Per-spread words**: 35-50 words per spread
- **Structure**: Three-act (25% beginning, 50% middle, 25% end)

## Quality Metrics
Source of truth: `backend/metrics/story_quality.py`

The quality judge evaluates:
- Engagement score
- Read-aloud score
- Emotional truth score
- Coherence score
- Chekhov score (setup/payoff)

## Industry Constraints
- Never create stories over 1000 words (industry standard limit)
- Target age range typically 4-7 years
